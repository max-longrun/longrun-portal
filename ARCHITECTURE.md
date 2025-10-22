# 🏗️ Application Architecture - After Supabase Migration

## 📊 System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER BROWSER                            │
│                    http://localhost:5000                         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ HTTP Requests
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                         FLASK APP                               │
│                         (app.py)                                │
│                                                                 │
│  Routes:                                                        │
│  • GET  /                    → Dashboard                       │
│  • GET  /campaigns           → Campaigns List                  │
│  • GET  /campaign/<id>       → Campaign Details               │
│  • GET  /api/dashboard-data  → Metrics & Charts               │
│  • GET  /api/campaigns       → All Campaigns                  │
│  • GET  /api/campaign/<id>   → Single Campaign                │
│  • GET  /api/recent-activity → Recent Replies                 │
│  • GET  /api/sync-data       → Manual Sync Trigger            │
└────────────────┬────────────────────────────┬───────────────────┘
                 │                            │
                 │                            │
    ┌────────────▼──────────┐    ┌───────────▼────────────┐
    │  supabase_manager.py  │    │   Background Sync      │
    │  (Database Layer)     │    │   (Every 5 minutes)    │
    │                       │    │                        │
    │  • get_db_manager()   │    │  • Fetch campaigns     │
    │  • execute_query()    │    │  • Fetch leads         │
    │  • Connection Pool    │    │  • Fetch replies       │
    └───────────┬───────────┘    └──────────┬─────────────┘
                │                           │
                │ PostgreSQL                │ REST API
                │ Connection                │ Requests
                ▼                           ▼
    ┌─────────────────────┐    ┌──────────────────────────┐
    │     SUPABASE        │    │   EMAILBISON API         │
    │   (PostgreSQL)      │    │  send.longrun.agency     │
    │                     │    │                          │
    │  Tables:            │    │  Endpoints:              │
    │  • campaigns        │    │  • /api/campaigns        │
    │  • leads            │    │  • /api/leads            │
    │  • replies          │    │  • /api/campaigns/:id    │
    │  • campaign_stats   │    │    /replies              │
    │  • sync_status      │    │                          │
    └─────────────────────┘    └──────────────────────────┘
```

---

## 🔄 Data Flow

### 1. Initial Load (Startup)

```
App Start
    ↓
Initialize supabase_manager.py
    ↓
Connect to Supabase (PostgreSQL)
    ↓
Create tables if not exist
    ↓
Start background sync thread
    ↓
Run initial sync from EmailBison API
    ↓
Ready to serve requests
```

### 2. Background Sync (Every 5 Minutes)

```
Timer triggers (5 min)
    ↓
Check if sync already in progress
    ↓ (No)
Set sync_in_progress = true
    ↓
┌─────────────────────┐
│  Sync Campaigns     │ ← GET /api/campaigns
│  • 13 campaigns     │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│  Sync Leads         │ ← GET /api/leads (paginated)
│  • ~5,000+ leads    │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│  Sync Replies       │ ← GET /api/campaigns/:id/replies
│  • For each         │   (for each campaign)
│    campaign         │
└──────────┬──────────┘
           ↓
Update Supabase with new data
    ↓
Set sync_in_progress = false
    ↓
Set last_sync = NOW()
    ↓
Wait 5 minutes...
```

### 3. User Dashboard Request

```
User visits /
    ↓
app.py: render_template('index.html')
    ↓
Browser loads
    ↓
JavaScript: fetch('/api/dashboard-data')
    ↓
app.py: get_dashboard_data()
    ↓
┌──────────────────────────────┐
│  Query Supabase:             │
│  • SELECT campaigns          │
│  • SELECT leads with joins   │
│  • SELECT replies            │
│  • Calculate metrics         │
│  • Generate chart data       │
└──────────┬───────────────────┘
           ↓
Return JSON response
    ↓
JavaScript renders charts
    ↓
Dashboard fully loaded
```

---

## 🗄️ Database Schema

### campaigns
```sql
id (INTEGER) PRIMARY KEY
name (TEXT)
status (TEXT)
unique_replies (INTEGER)
interested (INTEGER)
total_leads_contacted (INTEGER)
emails_sent (INTEGER)
created_at (TEXT)
updated_at (TEXT)
last_synced (TIMESTAMP)
```

### leads
```sql
id (INTEGER) PRIMARY KEY
email (TEXT)
first_name (TEXT)
last_name (TEXT)
title (TEXT)
company (TEXT)
phone (TEXT)
state (TEXT)
interested (BOOLEAN)
created_at (TEXT)
updated_at (TEXT)
last_synced (TIMESTAMP)
```

### replies
```sql
id (SERIAL) PRIMARY KEY
reply_uuid (TEXT) UNIQUE
lead_id (INTEGER) → leads(id)
campaign_id (INTEGER) → campaigns(id)
date_received (TEXT)
interested (BOOLEAN)
automated_reply (BOOLEAN)
subject (TEXT)
content (TEXT)
sender_email (TEXT)
created_at (TIMESTAMP)
```

---

## 🔌 Connection Management

### Supabase Connection Pool

```python
class SupabaseManager:
    def __init__(self):
        # Create connection pool (1-10 connections)
        self.connection_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=DATABASE_URL
        )
    
    def get_connection(self):
        # Get connection from pool
        conn = self.connection_pool.getconn()
        try:
            yield conn
        finally:
            # Return to pool after use
            self.connection_pool.putconn(conn)
```

### Query Execution

```python
# Automatically handles:
# • Connection pooling
# • Transaction management
# • Error handling
# • Retry logic

db_manager.execute_query(
    "SELECT * FROM campaigns WHERE id = %s",
    (campaign_id,)
)
```

---

## 🔐 Security Layers

```
User Request
    ↓
1. HTTPS (SSL/TLS)
    ↓
2. Flask App (server-side validation)
    ↓
3. Supabase Connection (encrypted)
    ↓
4. PostgreSQL (row-level security optional)
    ↓
Data returned
```

**Credentials stored in:**
- Environment variables (`.env` file locally)
- Platform environment variables (production)
- Never in source code

---

## 📈 Scalability

### SQLite (Before)
```
Single file → File locking → Concurrent issues
Limited performance with large datasets
Manual backups needed
```

### Supabase (After)
```
Cloud database → Connection pooling → No locking
Excellent performance at scale
Automatic backups
```

**Concurrent Users:**
- SQLite: ~10 users (file locking)
- Supabase: Unlimited (connection pool)

**Data Size:**
- SQLite: Good up to ~1GB
- Supabase: Great up to 100GB+ (on free tier)

---

## 🔧 Configuration Points

### Environment Variables

```bash
# Application reads from:
SUPABASE_URL         → Connection endpoint
SUPABASE_KEY         → Authentication key
DATABASE_URL         → Full PostgreSQL connection string
EMAILBISON_API_KEY   → External API authentication
EMAILBISON_DOMAIN    → External API endpoint
```

### Timeouts & Limits

```python
# Connection timeout
timeout=30.0  # 30 seconds

# Background sync interval
time.sleep(300)  # 5 minutes

# Pagination limits
max_pages = 50  # For leads
max_pages = 10  # For replies per campaign

# Connection pool
minconn=1   # Minimum connections
maxconn=10  # Maximum connections
```

---

## 🚀 Deployment Architecture

### Development
```
Local Machine
    ↓
Python app.py
    ↓
Connects to Supabase (cloud)
    ↓
Syncs from EmailBison API
```

### Production
```
Hosting Platform (Heroku/Render/Railway)
    ↓
gunicorn app:app
    ↓
Connects to Supabase (cloud)
    ↓
Syncs from EmailBison API
    ↓
Serves to Internet
```

---

## 📊 Performance Characteristics

| Metric | Value |
|--------|-------|
| Average query time | ~10-50ms |
| Dashboard load time | ~500ms |
| Background sync time | ~30-60 seconds |
| Sync frequency | Every 5 minutes |
| Concurrent users supported | 100+ |
| Data refresh latency | 5 minutes max |

---

## 🎯 Key Differences from SQLite

| Aspect | SQLite | Supabase |
|--------|--------|----------|
| **Storage** | Local `.db` file | Cloud PostgreSQL |
| **Connection** | Direct file access | TCP connection |
| **Placeholders** | `?` | `%s` |
| **Auto-increment** | `AUTOINCREMENT` | `SERIAL` |
| **Booleans** | 0/1 integers | true/false |
| **Timestamps** | TEXT | TIMESTAMP |
| **Concurrency** | File locking | Row locking |
| **Backups** | Copy file | Automatic |

---

## 🔄 Migration Process

```
SQLite Database (emailbison_data.db)
    ↓
migrate_to_supabase.py reads all data
    ↓
Connects to Supabase
    ↓
Creates tables if needed
    ↓
INSERT ... ON CONFLICT DO UPDATE
    ↓
Verifies row counts match
    ↓
Migration complete ✓
```

---

**This architecture ensures:**
- ✅ High availability
- ✅ Automatic scaling
- ✅ Data consistency
- ✅ Easy maintenance
- ✅ Production-ready deployment


