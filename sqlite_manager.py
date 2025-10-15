import sqlite3
import threading
import time
import queue
from datetime import datetime, timedelta
import requests
import json
from contextlib import contextmanager
import os

# EmailBison API configuration
EMAILBISON_DOMAIN = 'https://send.longrun.agency'
EMAILBISON_HEADERS = {
    'Authorization': 'Bearer 5|LJwTR33haOeU6bSlBGU08roquoklOlZg3CsNgEMtdd040014',
    'Accept': 'application/json'
}

# Database configuration
DATABASE_PATH = 'emailbison_data.db'

class SQLiteConnectionPool:
    """Connection pool for SQLite to handle concurrent access better"""
    
    def __init__(self, db_path, pool_size=10):
        self.db_path = db_path
        self.pool_size = pool_size
        self.pool = queue.Queue(maxsize=pool_size)
        self.lock = threading.Lock()
        self.init_pool()
    
    def init_pool(self):
        """Initialize the connection pool"""
        for _ in range(self.pool_size):
            conn = self.create_connection()
            self.pool.put(conn)
    
    def create_connection(self):
        """Create a new database connection with optimal settings"""
        conn = sqlite3.connect(
            self.db_path,
            timeout=30.0,
            check_same_thread=False
        )
        
        # Enable WAL mode for better concurrency
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA synchronous=NORMAL')
        conn.execute('PRAGMA cache_size=10000')
        conn.execute('PRAGMA temp_store=memory')
        conn.execute('PRAGMA mmap_size=268435456')  # 256MB
        conn.execute('PRAGMA optimize')
        
        return conn
    
    @contextmanager
    def get_connection(self):
        """Get a connection from the pool"""
        conn = None
        try:
            conn = self.pool.get(timeout=30)
            yield conn
        finally:
            if conn:
                self.pool.put(conn)

class SQLiteManager:
    def __init__(self, db_path=DATABASE_PATH):
        self.db_path = db_path
        self.pool = SQLiteConnectionPool(db_path)
        self.lock = threading.Lock()
        self.init_database()
    
    def init_database(self):
        """Initialize the database with all required tables"""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # Campaigns table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS campaigns (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    status TEXT,
                    unique_replies INTEGER DEFAULT 0,
                    interested INTEGER DEFAULT 0,
                    total_leads_contacted INTEGER DEFAULT 0,
                    emails_sent INTEGER DEFAULT 0,
                    created_at TEXT,
                    updated_at TEXT,
                    last_synced TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Leads table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS leads (
                    id INTEGER PRIMARY KEY,
                    email TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    title TEXT,
                    company TEXT,
                    phone TEXT,
                    state TEXT,
                    interested BOOLEAN DEFAULT 0,
                    created_at TEXT,
                    updated_at TEXT,
                    last_synced TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Add state column to existing tables (migration)
            try:
                cursor.execute('ALTER TABLE leads ADD COLUMN state TEXT')
                conn.commit()
                print("Added 'state' column to leads table")
            except sqlite3.OperationalError:
                # Column already exists
                pass
            
            # Replies table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS replies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reply_uuid TEXT UNIQUE,
                    lead_id INTEGER,
                    campaign_id INTEGER,
                    date_received TEXT,
                    interested BOOLEAN DEFAULT 0,
                    automated_reply BOOLEAN DEFAULT 0,
                    subject TEXT,
                    content TEXT,
                    sender_email TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (lead_id) REFERENCES leads (id),
                    FOREIGN KEY (campaign_id) REFERENCES campaigns (id)
                )
            ''')
            
            # Campaign stats table for time-based metrics
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS campaign_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    campaign_id INTEGER,
                    stat_date TEXT,
                    unique_replies INTEGER DEFAULT 0,
                    interested INTEGER DEFAULT 0,
                    total_leads_contacted INTEGER DEFAULT 0,
                    emails_sent INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (campaign_id) REFERENCES campaigns (id),
                    UNIQUE(campaign_id, stat_date)
                )
            ''')
            
            # Sync status table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sync_status (
                    id INTEGER PRIMARY KEY,
                    last_sync TEXT DEFAULT CURRENT_TIMESTAMP,
                    sync_in_progress BOOLEAN DEFAULT 0,
                    error_message TEXT
                )
            ''')
            
            # Insert initial sync status
            cursor.execute('''
                INSERT OR IGNORE INTO sync_status (id) VALUES (1)
            ''')
            
            conn.commit()
    
    def execute_query(self, query, params=None):
        """Execute a query with proper error handling and retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with self.pool.get_connection() as conn:
                    cursor = conn.cursor()
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)
                    result = cursor.fetchall()
                    conn.commit()
                    return result
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    time.sleep(0.1 * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    raise
    
    def execute_many(self, query, params_list):
        """Execute many queries with proper error handling and retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with self.pool.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.executemany(query, params_list)
                    conn.commit()
                    return
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    time.sleep(0.1 * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    raise

# Global database manager
db_manager = None
data_sync_manager = None

def get_db_manager():
    """Get or create database manager instance"""
    global db_manager
    if db_manager is None:
        db_manager = SQLiteManager()
    return db_manager

def get_sync_manager():
    """Get or create sync manager instance"""
    global data_sync_manager
    if data_sync_manager is None:
        data_sync_manager = DataSyncManager()
    return data_sync_manager

class DataSyncManager:
    def __init__(self):
        self.sync_in_progress = False
        self.last_sync = None
        self.sync_thread = None
        self.start_background_sync()
    
    def start_background_sync(self):
        """Start the background sync thread"""
        if self.sync_thread is None or not self.sync_thread.is_alive():
            self.sync_thread = threading.Thread(target=self._background_sync_loop, daemon=True)
            self.sync_thread.start()
    
    def _background_sync_loop(self):
        """Background sync loop that runs every 5 minutes"""
        while True:
            try:
                self.sync_data()
                time.sleep(300)  # Wait 5 minutes
            except Exception as e:
                print(f"Background sync error: {e}")
                time.sleep(60)  # Wait 1 minute on error
    
    def sync_data(self):
        """Sync data from EmailBison API to database"""
        if self.sync_in_progress:
            return
        
        self.sync_in_progress = True
        try:
            print(f"Starting data sync at {datetime.now()}")
            
            # Update sync status
            db_manager = get_db_manager()
            db_manager.execute_query(
                "UPDATE sync_status SET sync_in_progress = 1, last_sync = ? WHERE id = 1",
                (datetime.now().isoformat(),)
            )
            
            # Sync campaigns
            self._sync_campaigns()
            
            # Sync leads
            self._sync_leads()
            
            # Sync replies for all campaigns
            self._sync_replies()
            
            # Update sync status
            db_manager.execute_query(
                "UPDATE sync_status SET sync_in_progress = 0, last_sync = ?, error_message = NULL WHERE id = 1",
                (datetime.now().isoformat(),)
            )
            
            self.last_sync = datetime.now()
            print(f"Data sync completed at {self.last_sync}")
            
        except Exception as e:
            error_msg = str(e)
            print(f"Data sync error: {error_msg}")
            db_manager = get_db_manager()
            db_manager.execute_query(
                "UPDATE sync_status SET sync_in_progress = 0, error_message = ? WHERE id = 1",
                (error_msg,)
            )
        finally:
            self.sync_in_progress = False
    
    def _sync_campaigns(self):
        """Sync campaigns from EmailBison API"""
        try:
            campaigns_url = f'{EMAILBISON_DOMAIN}/api/campaigns'
            response = requests.get(campaigns_url, headers=EMAILBISON_HEADERS, timeout=30)
            response.raise_for_status()
            
            campaigns_data = response.json()
            campaigns_list = campaigns_data.get('data', [])
            
            # Don't clear existing campaigns - use INSERT OR REPLACE instead
            db_manager = get_db_manager()
            
            # Insert/update campaigns
            for campaign in campaigns_list:
                db_manager.execute_query(
                    "INSERT OR REPLACE INTO campaigns (id, name, status, unique_replies, interested, total_leads_contacted, emails_sent, created_at, updated_at, last_synced) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        campaign.get('id'),
                        campaign.get('name', ''),
                        campaign.get('status', ''),
                        campaign.get('unique_replies', 0),
                        campaign.get('interested', 0),
                        campaign.get('total_leads_contacted', 0),
                        campaign.get('emails_sent', 0),
                        campaign.get('created_at', ''),
                        campaign.get('updated_at', ''),
                        datetime.now().isoformat()
                    )
                )
            
            print(f"Synced {len(campaigns_list)} campaigns")
            
        except Exception as e:
            print(f"Error syncing campaigns: {e}")
            raise
    
    def _sync_leads(self):
        """Sync leads from EmailBison API"""
        try:
            # First, get all lead_ids that have replies but might be missing from leads table
            db_manager = get_db_manager()
            missing_lead_ids = db_manager.execute_query("""
                SELECT DISTINCT r.lead_id 
                FROM replies r 
                LEFT JOIN leads l ON r.lead_id = l.id 
                WHERE l.id IS NULL
            """)
            
            # Fetch specific missing leads first
            for lead_id_row in missing_lead_ids:
                lead_id = lead_id_row[0]
                try:
                    lead_url = f'{EMAILBISON_DOMAIN}/api/leads/{lead_id}'
                    response = requests.get(lead_url, headers=EMAILBISON_HEADERS, timeout=30)
                    response.raise_for_status()
                    
                    lead_data = response.json()
                    lead = lead_data.get('data')
                    if lead:
                        # Check if lead is interested (from any campaign)
                        is_interested = False
                        for campaign_data in lead.get('lead_campaign_data', []):
                            if campaign_data.get('interested'):
                                is_interested = True
                                break
                        
                        # Extract state from custom_variables (array format)
                        state = None
                        custom_vars = lead.get('custom_variables', [])
                        if isinstance(custom_vars, list):
                            for var in custom_vars:
                                if var.get('name') == 'state':
                                    state = var.get('value', '')
                                    break
                        
                        db_manager.execute_query(
                            "INSERT OR REPLACE INTO leads (id, email, first_name, last_name, title, company, phone, state, interested, created_at, updated_at, last_synced) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (
                                lead.get('id'),
                                lead.get('email', ''),
                                lead.get('first_name', ''),
                                lead.get('last_name', ''),
                                lead.get('title', ''),
                                lead.get('company', ''),
                                lead.get('phone', ''),
                                state if state else None,
                                is_interested,
                                lead.get('created_at', ''),
                                lead.get('updated_at', ''),
                                datetime.now().isoformat()
                            )
                        )
                        print(f"Fetched missing lead {lead_id}")
                except Exception as e:
                    print(f"Error fetching lead {lead_id}: {e}")
                    continue
            
            # Fetch leads with pagination (reduced limit since we fetched missing ones)
            all_leads = []
            page = 1
            max_pages = 50  # Reduced limit for performance
            
            while page <= max_pages:
                leads_url = f'{EMAILBISON_DOMAIN}/api/leads?page={page}&per_page=100'
                response = requests.get(leads_url, headers=EMAILBISON_HEADERS, timeout=30)
                response.raise_for_status()
                
                leads_data = response.json()
                leads_list = leads_data.get('data', [])
                
                if not leads_list:
                    break
                
                all_leads.extend(leads_list)
                
                # Check pagination
                meta = leads_data.get('meta', {})
                if meta.get('current_page', page) >= meta.get('last_page', page):
                    break
                page += 1
            
            # Don't clear existing leads - use INSERT OR REPLACE instead
            db_manager = get_db_manager()
            
            # Insert/update leads
            for lead in all_leads:
                # Check if lead is interested (from any campaign)
                is_interested = False
                for campaign_data in lead.get('lead_campaign_data', []):
                    if campaign_data.get('interested'):
                        is_interested = True
                        break
                
                # Extract state from custom_variables (array format)
                state = None
                custom_vars = lead.get('custom_variables', [])
                if isinstance(custom_vars, list):
                    for var in custom_vars:
                        if var.get('name') == 'state':
                            state = var.get('value', '')
                            break
                
                db_manager.execute_query(
                    "INSERT OR REPLACE INTO leads (id, email, first_name, last_name, title, company, phone, state, interested, created_at, updated_at, last_synced) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        lead.get('id'),
                        lead.get('email', ''),
                        lead.get('first_name', ''),
                        lead.get('last_name', ''),
                        lead.get('title', ''),
                        lead.get('company', ''),
                        lead.get('phone', ''),
                        state if state else None,
                        is_interested,
                        lead.get('created_at', ''),
                        lead.get('updated_at', ''),
                        datetime.now().isoformat()
                    )
                )
            
            print(f"Synced {len(all_leads)} leads")
            
        except Exception as e:
            print(f"Error syncing leads: {e}")
            raise
    
    def _sync_replies(self):
        """Sync replies from all campaigns"""
        try:
            # Get all campaign IDs
            db_manager = get_db_manager()
            campaigns = db_manager.execute_query("SELECT id FROM campaigns")
            campaign_ids = [row[0] for row in campaigns]
            
            # Don't clear existing replies - use INSERT OR REPLACE instead
            
            total_replies = 0
            
            for campaign_id in campaign_ids:
                try:
                    # Fetch replies with pagination
                    page = 1
                    max_pages = 10  # Limit for performance
                    
                    while page <= max_pages:
                        replies_url = f'{EMAILBISON_DOMAIN}/api/campaigns/{campaign_id}/replies?page={page}&per_page=100'
                        response = requests.get(replies_url, headers=EMAILBISON_HEADERS, timeout=30)
                        response.raise_for_status()
                        
                        replies_data = response.json()
                        replies_list = replies_data.get('data', [])
                        
                        if not replies_list:
                            break
                        
                        # Insert/update replies
                        for reply in replies_list:
                            lead_id = reply.get('lead_id')
                            # Get UUID from the correct field - EmailBison uses 'uuid' not 'reply_uuid'
                            reply_uuid = reply.get('uuid', '') or reply.get('reply_uuid', '')
                            
                            # Log if UUID is missing (should be rare now)
                            if not reply_uuid or reply_uuid.strip() == '':
                                print(f"Warning: No UUID found for reply from lead {lead_id} in campaign {campaign_id}")
                                continue  # Skip replies without UUID
                            
                            # Try to get content from different possible fields (from API docs: text_body, html_body)
                            content = reply.get('text_body', '') or reply.get('html_body', '') or reply.get('content', '') or reply.get('message', '') or reply.get('body', '')
                            subject = reply.get('subject', '') or reply.get('title', '')
                            
                            db_manager.execute_query(
                                "INSERT OR REPLACE INTO replies (reply_uuid, lead_id, campaign_id, date_received, interested, automated_reply, subject, content, sender_email) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                (
                                    reply_uuid,
                                    lead_id,
                                    campaign_id,
                                    reply.get('date_received', ''),
                                    reply.get('interested', False),
                                    reply.get('automated_reply', False),
                                    subject,
                                    content,
                                    reply.get('sender_email', '')
                                )
                            )
                            total_replies += 1
                        
                        # Check pagination
                        meta = replies_data.get('meta', {})
                        if meta.get('current_page', page) >= meta.get('last_page', page):
                            break
                        page += 1
                
                except Exception as e:
                    print(f"Error syncing replies for campaign {campaign_id}: {e}")
                    continue
            
            print(f"Synced {total_replies} replies")
            
        except Exception as e:
            print(f"Error syncing replies: {e}")
            raise

# Initialize database and start sync
if __name__ == '__main__':
    # This will run the sync immediately and start background sync
    get_sync_manager().sync_data()
