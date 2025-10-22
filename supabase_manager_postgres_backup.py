import psycopg
from psycopg import pool
import threading
import time
from datetime import datetime, timedelta
import requests
import json
import os
from contextlib import contextmanager

# EmailBison API configuration
EMAILBISON_DOMAIN = os.environ.get('EMAILBISON_DOMAIN', 'https://send.longrun.agency')
EMAILBISON_API_KEY = os.environ.get('EMAILBISON_API_KEY', '5|LJwTR33haOeU6bSlBGU08roquoklOlZg3CsNgEMtdd040014')
EMAILBISON_HEADERS = {
    'Authorization': f'Bearer {EMAILBISON_API_KEY}',
    'Accept': 'application/json'
}

# Supabase configuration
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://ocoihazbvkyjuexmhpnj.supabase.co')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', 'sb_secret_LaBpA-IgbOThrRNoNGPBGQ_EpPhp8K9')

# PostgreSQL connection string for Supabase
# Direct connection to Supabase PostgreSQL database
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres.ocoihazbvkyjuexmhpnj:NGs9ygm9OBk9lbBt@aws-1-eu-central-1.pooler.supabase.com:5432/postgres')

class SupabaseManager:
    """Database manager for Supabase (PostgreSQL)"""
    
    def __init__(self, database_url=DATABASE_URL):
        self.database_url = database_url
        self.connection_pool = None
        self.lock = threading.Lock()
        self.init_connection_pool()
        self.init_database()
    
    def init_connection_pool(self):
        """Initialize the connection pool"""
        try:
            self.connection_pool = psycopg.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=self.database_url,
                options='-c statement_timeout=30000'  # 30 second timeout
            )
            print("Connected to Supabase (PostgreSQL)")
        except Exception as e:
            print(f"Error connecting to Supabase: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """Get a connection from the pool"""
        conn = None
        try:
            conn = self.connection_pool.getconn()
            yield conn
        finally:
            if conn:
                self.connection_pool.putconn(conn)
    
    def init_database(self):
        """Initialize the database with all required tables"""
        with self.get_connection() as conn:
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
                    last_synced TIMESTAMP DEFAULT NOW()
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
                    interested BOOLEAN DEFAULT false,
                    created_at TEXT,
                    updated_at TEXT,
                    last_synced TIMESTAMP DEFAULT NOW()
                )
            ''')
            
            # Replies table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS replies (
                    id SERIAL PRIMARY KEY,
                    reply_uuid TEXT UNIQUE,
                    lead_id INTEGER,
                    campaign_id INTEGER,
                    date_received TEXT,
                    interested BOOLEAN DEFAULT false,
                    automated_reply BOOLEAN DEFAULT false,
                    subject TEXT,
                    content TEXT,
                    sender_email TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    FOREIGN KEY (lead_id) REFERENCES leads (id),
                    FOREIGN KEY (campaign_id) REFERENCES campaigns (id)
                )
            ''')
            
            # Campaign stats table for time-based metrics
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS campaign_stats (
                    id SERIAL PRIMARY KEY,
                    campaign_id INTEGER,
                    stat_date TEXT,
                    unique_replies INTEGER DEFAULT 0,
                    interested INTEGER DEFAULT 0,
                    total_leads_contacted INTEGER DEFAULT 0,
                    emails_sent INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW(),
                    FOREIGN KEY (campaign_id) REFERENCES campaigns (id),
                    UNIQUE(campaign_id, stat_date)
                )
            ''')
            
            # Sync status table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sync_status (
                    id INTEGER PRIMARY KEY,
                    last_sync TIMESTAMP DEFAULT NOW(),
                    sync_in_progress BOOLEAN DEFAULT false,
                    error_message TEXT
                )
            ''')
            
            # Insert initial sync status
            cursor.execute('''
                INSERT INTO sync_status (id, last_sync, sync_in_progress)
                VALUES (1, NOW(), false)
                ON CONFLICT (id) DO NOTHING
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_replies_campaign_id ON replies(campaign_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_replies_lead_id ON replies(lead_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_replies_date_received ON replies(date_received)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_replies_interested ON replies(interested)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_leads_state ON leads(state)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns(status)')
            
            conn.commit()
            print("Database schema initialized")
    
    def execute_query(self, query, params=None):
        """Execute a query and return results"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    if params:
                        cursor.execute(query, params)
                    else:
                        cursor.execute(query)
                    
                    # Check if query returns results
                    if cursor.description:
                        result = cursor.fetchall()
                    else:
                        result = []
                    
                    conn.commit()
                    return result
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(0.1 * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    print(f"Query error: {e}")
                    raise
    
    def execute_many(self, query, params_list):
        """Execute many queries with proper error handling"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.executemany(query, params_list)
                    conn.commit()
                    return
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(0.1 * (attempt + 1))
                    continue
                else:
                    print(f"Execute many error: {e}")
                    raise

# Global database manager
db_manager = None
data_sync_manager = None

def get_db_manager():
    """Get or create database manager instance"""
    global db_manager
    if db_manager is None:
        db_manager = SupabaseManager()
    return db_manager

def get_sync_manager():
    """Get or create sync manager instance"""
    global data_sync_manager
    if data_sync_manager is None:
        data_sync_manager = DataSyncManager()
    return data_sync_manager

class DataSyncManager:
    """Manages background data synchronization from EmailBison API"""
    
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
            print("Background sync started")
    
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
        """Sync data from EmailBison API to Supabase"""
        if self.sync_in_progress:
            print("Sync already in progress, skipping...")
            return
        
        self.sync_in_progress = True
        try:
            print(f"\n{'='*60}")
            print(f"Starting data sync at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*60}")
            
            # Update sync status
            db_manager = get_db_manager()
            db_manager.execute_query(
                "UPDATE sync_status SET sync_in_progress = true, last_sync = NOW() WHERE id = 1"
            )
            
            # Sync campaigns
            print("\n📊 Syncing campaigns...")
            self._sync_campaigns()
            
            # Sync leads
            print("\n👥 Syncing leads...")
            self._sync_leads()
            
            # Sync replies for all campaigns
            print("\n💬 Syncing replies...")
            self._sync_replies()
            
            # Update sync status
            db_manager.execute_query(
                "UPDATE sync_status SET sync_in_progress = false, last_sync = NOW(), error_message = NULL WHERE id = 1"
            )
            
            self.last_sync = datetime.now()
            print(f"\n{'='*60}")
            print(f"Data sync completed at {self.last_sync.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*60}\n")
            
        except Exception as e:
            error_msg = str(e)
            print(f"\nData sync error: {error_msg}")
            db_manager = get_db_manager()
            db_manager.execute_query(
                "UPDATE sync_status SET sync_in_progress = false, error_message = %s WHERE id = 1",
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
            
            db_manager = get_db_manager()
            
            # Insert/update campaigns using UPSERT (INSERT ... ON CONFLICT)
            for campaign in campaigns_list:
                db_manager.execute_query('''
                    INSERT INTO campaigns (id, name, status, unique_replies, interested, 
                                         total_leads_contacted, emails_sent, created_at, updated_at, last_synced)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name,
                        status = EXCLUDED.status,
                        unique_replies = EXCLUDED.unique_replies,
                        interested = EXCLUDED.interested,
                        total_leads_contacted = EXCLUDED.total_leads_contacted,
                        emails_sent = EXCLUDED.emails_sent,
                        updated_at = EXCLUDED.updated_at,
                        last_synced = NOW()
                ''', (
                    campaign.get('id'),
                    campaign.get('name', ''),
                    campaign.get('status', ''),
                    campaign.get('unique_replies', 0),
                    campaign.get('interested', 0),
                    campaign.get('total_leads_contacted', 0),
                    campaign.get('emails_sent', 0),
                    campaign.get('created_at', ''),
                    campaign.get('updated_at', '')
                ))
            
            print(f"   Synced {len(campaigns_list)} campaigns")
            
        except Exception as e:
            print(f"   Error syncing campaigns: {e}")
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
                        self._insert_or_update_lead(lead)
                        print(f"   Fetched missing lead {lead_id}")
                except Exception as e:
                    print(f"   Error fetching lead {lead_id}: {e}")
                    continue
            
            # Fetch leads with pagination
            all_leads = []
            page = 1
            max_pages = 50
            
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
            
            # Insert/update leads
            for lead in all_leads:
                self._insert_or_update_lead(lead)
            
            print(f"   Synced {len(all_leads)} leads")
            
        except Exception as e:
            print(f"   Error syncing leads: {e}")
            raise
    
    def _insert_or_update_lead(self, lead):
        """Helper method to insert or update a single lead"""
        db_manager = get_db_manager()
        
        # Check if lead is interested (from any campaign)
        is_interested = False
        for campaign_data in lead.get('lead_campaign_data', []):
            if campaign_data.get('interested'):
                is_interested = True
                break
        
        # Extract state from custom_variables
        state = None
        custom_vars = lead.get('custom_variables', [])
        if isinstance(custom_vars, list):
            for var in custom_vars:
                if var.get('name') == 'state':
                    state = var.get('value', '')
                    break
        
        db_manager.execute_query('''
            INSERT INTO leads (id, email, first_name, last_name, title, company, phone, 
                             state, interested, created_at, updated_at, last_synced)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (id) DO UPDATE SET
                email = EXCLUDED.email,
                first_name = EXCLUDED.first_name,
                last_name = EXCLUDED.last_name,
                title = EXCLUDED.title,
                company = EXCLUDED.company,
                phone = EXCLUDED.phone,
                state = EXCLUDED.state,
                interested = EXCLUDED.interested,
                updated_at = EXCLUDED.updated_at,
                last_synced = NOW()
        ''', (
            lead.get('id'),
            lead.get('email', ''),
            lead.get('first_name', ''),
            lead.get('last_name', ''),
            lead.get('title', ''),
            lead.get('company', ''),
            lead.get('phone', ''),
            state,
            is_interested,
            lead.get('created_at', ''),
            lead.get('updated_at', '')
        ))
    
    def _sync_replies(self):
        """Sync replies from all campaigns"""
        try:
            # Get all campaign IDs
            db_manager = get_db_manager()
            campaigns = db_manager.execute_query("SELECT id FROM campaigns")
            campaign_ids = [row[0] for row in campaigns]
            
            total_replies = 0
            
            for campaign_id in campaign_ids:
                try:
                    # Fetch replies with pagination
                    page = 1
                    max_pages = 10
                    
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
                            reply_uuid = reply.get('uuid', '') or reply.get('reply_uuid', '')
                            
                            if not reply_uuid or reply_uuid.strip() == '':
                                continue
                            
                            content = reply.get('text_body', '') or reply.get('html_body', '') or reply.get('content', '')
                            subject = reply.get('subject', '') or reply.get('title', '')
                            
                            db_manager.execute_query('''
                                INSERT INTO replies (reply_uuid, lead_id, campaign_id, date_received, 
                                                   interested, automated_reply, subject, content, sender_email)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (reply_uuid) DO UPDATE SET
                                    interested = EXCLUDED.interested,
                                    automated_reply = EXCLUDED.automated_reply,
                                    subject = EXCLUDED.subject,
                                    content = EXCLUDED.content,
                                    sender_email = EXCLUDED.sender_email
                            ''', (
                                reply_uuid,
                                lead_id,
                                campaign_id,
                                reply.get('date_received', ''),
                                reply.get('interested', False),
                                reply.get('automated_reply', False),
                                subject,
                                content,
                                reply.get('sender_email', '')
                            ))
                            total_replies += 1
                        
                        # Check pagination
                        meta = replies_data.get('meta', {})
                        if meta.get('current_page', page) >= meta.get('last_page', page):
                            break
                        page += 1
                
                except Exception as e:
                    print(f"   Error syncing replies for campaign {campaign_id}: {e}")
                    continue
            
            print(f"   Synced {total_replies} replies")
            
        except Exception as e:
            print(f"   Error syncing replies: {e}")
            raise

# Initialize on import
if __name__ == '__main__':
    # Test connection
    print("Testing Supabase connection...")
    manager = get_db_manager()
    print("Starting initial sync...")
    get_sync_manager().sync_data()

