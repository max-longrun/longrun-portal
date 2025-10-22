from flask import Flask, render_template, jsonify
import os
from datetime import datetime, timedelta
import random
import requests
from collections import Counter
from supabase_manager_postgres_backup import get_db_manager, get_sync_manager

app = Flask(__name__)

# EmailBison API configuration (kept for manual sync if needed)
EMAILBISON_API_KEY = os.environ.get('EMAILBISON_API_KEY', '5|LJwTR33haOeU6bSlBGU08roquoklOlZg3CsNgEMtdd040014')
EMAILBISON_DOMAIN = os.environ.get('EMAILBISON_DOMAIN', 'https://send.longrun.agency')
EMAILBISON_HEADERS = {
    'Authorization': f'Bearer {EMAILBISON_API_KEY}',
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/campaigns')
def campaigns():
    """Campaigns page"""
    return render_template('campaigns.html')

@app.route('/campaign/<int:campaign_id>')
def campaign_detail(campaign_id):
    """Individual campaign detail page"""
    return render_template('campaign_detail.html', campaign_id=campaign_id)

@app.route('/api/campaigns')
def get_campaigns():
    """Get all campaigns with stats, sorted by status"""
    try:
        # Fetch campaigns data from database
        campaigns_data = fetch_campaigns_from_db()
        campaigns_list = campaigns_data.get('campaigns', [])
        
        # Sort campaigns by status: active -> paused -> finished
        status_order = {'active': 0, 'paused': 1, 'finished': 2, 'completed': 2, 'draft': 3}
        
        def sort_key(campaign):
            status = campaign.get('status', '').lower()
            return status_order.get(status, 999)
        
        sorted_campaigns = sorted(campaigns_list, key=sort_key)
        
        # Add calculated stats to each campaign
        for campaign in sorted_campaigns:
            campaign_id = campaign.get('id')
            if campaign_id:
                # Add additional calculated metrics
                total_contacted = campaign.get('total_leads_contacted', 0)
                interested = campaign.get('interested', 0)
                unique_replies = int(campaign.get('unique_replies', 0))
                
                # Calculate rates
                reply_rate = (unique_replies / total_contacted * 100) if total_contacted > 0 else 0
                positive_rate = (interested / unique_replies * 100) if unique_replies > 0 else 0
                
                campaign['reply_rate'] = round(reply_rate, 1)
                campaign['positive_rate'] = round(positive_rate, 1)
                campaign['formatted_created_at'] = format_date(campaign.get('created_at', ''))
                campaign['formatted_updated_at'] = format_date(campaign.get('updated_at', ''))
        
        return jsonify({
            'success': True,
            'campaigns': sorted_campaigns,
            'total': len(sorted_campaigns)
        })
        
    except Exception as e:
        print(f"Error fetching campaigns data: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'campaigns': [],
            'total': 0
        })

@app.route('/api/campaign/<int:campaign_id>')
def get_campaign_detail(campaign_id):
    """Get individual campaign details with metrics"""
    try:
        # Fetch campaigns data from database
        campaigns_data = fetch_campaigns_from_db()
        campaigns_list = campaigns_data.get('campaigns', [])
        
        # Find the specific campaign
        campaign = None
        for c in campaigns_list:
            if c.get('id') == campaign_id:
                campaign = c
                break
        
        if not campaign:
            return jsonify({
                'success': False,
                'error': 'Campaign not found',
                'campaign': None
            })
        
        # Add calculated stats to campaign
        total_contacted = campaign.get('total_leads_contacted', 0)
        interested = campaign.get('interested', 0)
        unique_replies = int(campaign.get('unique_replies', 0))
        
        # Calculate rates
        reply_rate = (unique_replies / total_contacted * 100) if total_contacted > 0 else 0
        positive_rate = (interested / unique_replies * 100) if unique_replies > 0 else 0
        
        campaign['reply_rate'] = round(reply_rate, 1)
        campaign['positive_rate'] = round(positive_rate, 1)
        campaign['formatted_created_at'] = format_date(campaign.get('created_at', ''))
        
        return jsonify({
            'success': True,
            'campaign': campaign
        })
        
    except Exception as e:
        print(f"Error fetching campaign details: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'campaign': None
        })

@app.route('/api/campaign/<int:campaign_id>/replies')
def get_campaign_replies(campaign_id):
    """Get replies for a specific campaign from database"""
    try:
        # Fetch replies from database
        db_manager = get_db_manager()
        replies = db_manager.execute_query("""
            SELECT r.reply_uuid, r.lead_id, r.date_received, r.interested, r.automated_reply, 
                   r.subject, r.content, r.sender_email,
                   l.first_name, l.last_name, l.email, l.title, l.company
            FROM replies r
            LEFT JOIN leads l ON r.lead_id = l.id
            WHERE r.campaign_id = %s
            AND r.automated_reply = false
            ORDER BY r.date_received DESC
        """, (campaign_id,))
        
        # Process ALL replies without deduplication
        all_replies_list = []
        for reply in replies:
            all_replies_list.append({
                'reply_uuid': reply[0],
                'lead_id': reply[1],
                'date_received': reply[2],
                'interested': bool(reply[3]),
                'automated_reply': bool(reply[4]),
                'subject': reply[5],
                'content': reply[6],
                'sender_email': reply[7],
                'lead_name': f"{reply[8] or ''} {reply[9] or ''}".strip(),
                'lead_email': reply[10],
                'lead_title': reply[11],
                'lead_company': reply[12]
            })
        
        # Process replies for "All" tab - deduplicate by lead_id, keeping latest reply
        deduplicated_replies = {}
        for reply_data in all_replies_list:
            lead_id = reply_data['lead_id']
            if lead_id not in deduplicated_replies:
                deduplicated_replies[lead_id] = reply_data
        
        deduplicated_list = list(deduplicated_replies.values())
        deduplicated_list.sort(key=lambda x: x['date_received'], reverse=True)
        
        # Separate positive replies - NO deduplication
        positive_replies = [r for r in all_replies_list if r['interested']]
        
        return jsonify({
            'success': True,
            'all_replies': deduplicated_list,
            'positive_replies': positive_replies,
            'total_replies': len(deduplicated_list),
            'positive_count': len(positive_replies)
        })
        
    except Exception as e:
        print(f"Error fetching campaign replies: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'all_replies': [],
            'positive_replies': [],
            'total_replies': 0,
            'positive_count': 0
        })

@app.route('/api/recent-activity')
def get_recent_activity():
    """Get recent replies activity across all campaigns from database"""
    try:
        db_manager = get_db_manager()
        
        # Fetch recent replies for "All" tab - deduplicated by lead_id
        all_replies_raw = db_manager.execute_query("""
            SELECT r.reply_uuid, r.lead_id, r.campaign_id, r.date_received, r.interested, 
                   r.subject, r.content, r.sender_email,
                   l.first_name, l.last_name, l.email, l.title, l.company,
                   c.name as campaign_name
            FROM replies r
            LEFT JOIN leads l ON r.lead_id = l.id
            LEFT JOIN campaigns c ON r.campaign_id = c.id
            WHERE r.automated_reply = false
            ORDER BY r.date_received DESC
            LIMIT 20
        """)
        
        # Process replies for "All" tab - deduplicate by lead_id, keeping latest reply
        processed_all_replies = {}
        for reply in all_replies_raw:
            lead_id = reply[1]
            if lead_id not in processed_all_replies:
                processed_all_replies[lead_id] = {
                    'reply_uuid': reply[0],
                    'lead_id': lead_id,
                    'campaign_id': reply[2],
                    'date_received': reply[3],
                    'interested': bool(reply[4]),
                    'subject': reply[5],
                    'content': reply[6],
                    'sender_email': reply[7],
                    'lead_name': f"{reply[8] or ''} {reply[9] or ''}".strip(),
                    'lead_email': reply[10],
                    'lead_title': reply[11],
                    'lead_company': reply[12],
                    'campaign_name': reply[13]
                }
        
        # Convert to list and sort by date
        all_replies_list = list(processed_all_replies.values())
        all_replies_list.sort(key=lambda x: x['date_received'], reverse=True)
        
        # Get latest 10 replies for "All" tab
        latest_replies = all_replies_list[:10]
        
        # Fetch positive replies for "Positive" tab - NO deduplication, just last 10
        positive_replies_raw = db_manager.execute_query("""
            SELECT r.reply_uuid, r.lead_id, r.campaign_id, r.date_received, r.interested, 
                   r.subject, r.content, r.sender_email,
                   l.first_name, l.last_name, l.email, l.title, l.company,
                   c.name as campaign_name
            FROM replies r
            LEFT JOIN leads l ON r.lead_id = l.id
            LEFT JOIN campaigns c ON r.campaign_id = c.id
            WHERE r.automated_reply = false AND r.interested = true
            ORDER BY r.date_received DESC
            LIMIT 10
        """)
        
        # Process positive replies - NO deduplication
        positive_replies = []
        for reply in positive_replies_raw:
            positive_replies.append({
                'reply_uuid': reply[0],
                'lead_id': reply[1],
                'campaign_id': reply[2],
                'date_received': reply[3],
                'interested': bool(reply[4]),
                'subject': reply[5],
                'content': reply[6],
                'sender_email': reply[7],
                'lead_name': f"{reply[8] or ''} {reply[9] or ''}".strip(),
                'lead_email': reply[10],
                'lead_title': reply[11],
                'lead_company': reply[12],
                'campaign_name': reply[13]
            })
        
        return jsonify({
            'success': True,
            'all_replies': latest_replies,
            'positive_replies': positive_replies
        })
        
    except Exception as e:
        print(f"Error fetching recent activity: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'all_replies': [],
            'positive_replies': []
        })

@app.route('/api/dashboard-data')
def get_dashboard_data():
    """
    API endpoint to fetch dashboard data from database with time frame filtering
    """
    try:
        from flask import request
        
        # Get timeframe parameter
        timeframe = request.args.get('timeframe', '7d')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Calculate date range
        date_range = calculate_date_range(timeframe, start_date, end_date)
        
        # Fetch data from database
        leads_data = fetch_leads_from_db()
        campaigns_data = fetch_campaigns_from_db()
        
        # Process the data with time filtering
        metrics = calculate_metrics_from_db(leads_data, campaigns_data, date_range)
        chart_data = generate_chart_data_from_db(leads_data, campaigns_data, date_range)
        
        data = {
            'metrics': metrics,
            'chart_data': chart_data,
            'timeframe_label': date_range['label']
        }
        return jsonify(data)
    except Exception as e:
        print(f"Error fetching EmailBison data: {e}")
        import traceback
        traceback.print_exc()
        # Fallback to sample data if API fails
        data = {
            'metrics': {
                'total_leads': 0,
                'reply_rate': 0,
                'reply_count': 0,
                'positive_rate': 0,
                'prospects_contacted': 0,
                'emails_sent': 0
            },
            'chart_data': {
                'leads_over_time': generate_sample_leads_data(),
                'email_performance': generate_sample_email_data(),
                'conversion_funnel': generate_funnel_data(),
                'lead_sources': generate_source_data()
            },
            'timeframe_label': 'Last 7 Days'
        }
        return jsonify(data)

@app.route('/api/custom-timeframe-data')
def get_custom_timeframe_data():
    """
    API endpoint specifically for custom timeframe with enhanced loading and error handling
    """
    try:
        from flask import request
        
        # Get custom date parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not start_date or not end_date:
            return jsonify({
                'success': False,
                'error': 'Start date and end date are required'
            })
        
        # Calculate date range
        date_range = calculate_date_range('custom', start_date, end_date)
        
        print(f"Processing custom timeframe: {date_range['label']}")
        
        # Fetch data from database
        leads_data = fetch_leads_from_db()
        campaigns_data = fetch_campaigns_from_db()
        
        # Process the data with time filtering
        metrics = calculate_metrics_from_db(leads_data, campaigns_data, date_range)
        chart_data = generate_chart_data_from_db(leads_data, campaigns_data, date_range)
        
        data = {
            'success': True,
            'metrics': metrics,
            'chart_data': chart_data,
            'timeframe_label': date_range['label']
        }
        return jsonify(data)
        
    except Exception as e:
        print(f"Error fetching custom timeframe data: {e}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'error': str(e),
            'metrics': {
                'total_leads': 0,
                'reply_rate': 0,
                'reply_count': 0,
                'positive_rate': 0,
                'prospects_contacted': 0,
                'emails_sent': 0
            },
            'chart_data': {
                'replies_over_time': {'labels': [], 'all_values': [], 'positive_values': []},
                'campaign_breakdown': {'labels': [], 'values': []},
                'reply_status': {'labels': [], 'values': []},
                'leads_by_title': {'labels': [], 'values': []},
                'leads_by_location': {'labels': [], 'values': []},
                'campaign_performance': {'labels': [], 'rates': [], 'positive_counts': [], 'contacted_counts': []},
                'map_locations': []
            },
            'timeframe_label': 'Custom Range'
        })

def format_date(date_string):
    """Format date string to readable format"""
    if not date_string:
        return 'N/A'
    try:
        from datetime import datetime
        # Handle different date formats
        if 'T' in date_string:
            dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        else:
            dt = datetime.fromisoformat(date_string)
        return dt.strftime('%b %d, %Y')
    except:
        return date_string

def calculate_date_range(timeframe, start_date=None, end_date=None):
    """Calculate start and end dates based on timeframe"""
    from dateutil.relativedelta import relativedelta
    
    today = datetime.now().date()
    
    if timeframe == '7d':
        start = today - timedelta(days=7)
        end = today
        label = 'Last 7 Days'
    elif timeframe == 'mtd':
        start = today.replace(day=1)
        end = today
        label = 'Month to Date'
    elif timeframe == 'lm':
        # Last month
        first_of_this_month = today.replace(day=1)
        last_month_end = first_of_this_month - timedelta(days=1)
        start = last_month_end.replace(day=1)
        end = last_month_end
        label = f'{start.strftime("%B %Y")}'
    elif timeframe == 'custom' and start_date and end_date:
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
        label = f'{start.strftime("%b %d")} - {end.strftime("%b %d, %Y")}'
    else:  # all time
        start = datetime(2020, 1, 1).date()
        end = today
        label = 'All Time'
    
    return {
        'start': start,
        'end': end,
        'label': label
    }

def generate_sample_leads_data():
    """Generate sample leads data for the past 30 days"""
    labels = []
    values = []
    for i in range(30, 0, -1):
        date = datetime.now() - timedelta(days=i)
        labels.append(date.strftime('%b %d'))
        values.append(random.randint(20, 80))
    
    return {'labels': labels, 'values': values}

def generate_sample_email_data():
    """Generate sample email performance data"""
    return {
        'labels': ['Sent', 'Opened', 'Clicked', 'Replied'],
        'values': [892, 645, 234, 156]
    }

def generate_funnel_data():
    """Generate conversion funnel data"""
    return {
        'labels': ['Leads Generated', 'Contacted', 'Responded', 'Qualified', 'Converted'],
        'values': [1247, 892, 234, 156, 102]
    }

def generate_source_data():
    """Generate lead source distribution data"""
    return {
        'labels': ['LinkedIn', 'Email Campaign', 'Website Form', 'Referral', 'Cold Outreach'],
        'values': [35, 28, 18, 12, 7]
    }

# EmailBison API integration functions
# Database functions
def fetch_leads_from_db():
    """Fetch leads from database"""
    try:
        db_manager = get_db_manager()
        leads = db_manager.execute_query("""
            SELECT id, email, first_name, last_name, title, company, phone, interested, created_at, updated_at
            FROM leads
        """)
        
        leads_list = []
        for lead in leads:
            leads_list.append({
                'id': lead[0],
                'email': lead[1],
                'first_name': lead[2],
                'last_name': lead[3],
                'title': lead[4],
                'company': lead[5],
                'phone': lead[6],
                'interested': bool(lead[7]),
                'created_at': lead[8],
                'updated_at': lead[9]
            })
        
        return {'leads': leads_list}
    except Exception as e:
        print(f"Error fetching leads from database: {e}")
        return {'leads': []}

def fetch_campaigns_from_db():
    """Fetch campaigns from database"""
    try:
        db_manager = get_db_manager()
        campaigns = db_manager.execute_query("""
            SELECT id, name, status, unique_replies, interested, total_leads_contacted, emails_sent, created_at, updated_at
            FROM campaigns
        """)
        
        campaigns_list = []
        for campaign in campaigns:
            campaigns_list.append({
                'id': campaign[0],
                'name': campaign[1],
                'status': campaign[2],
                'unique_replies': campaign[3],
                'interested': campaign[4],
                'total_leads_contacted': campaign[5],
                'emails_sent': campaign[6],
                'created_at': campaign[7],
                'updated_at': campaign[8]
            })
        
        return {'campaigns': campaigns_list}
    except Exception as e:
        print(f"Error fetching campaigns from database: {e}")
        return {'campaigns': []}

def calculate_metrics_from_db(leads_data, campaigns_data, date_range):
    """Calculate dashboard metrics from database data"""
    campaigns_list = campaigns_data.get('campaigns', [])
    start_date = date_range['start']
    end_date = date_range['end']
    
    # Initialize counters
    total_interested = 0
    total_unique_replies = 0
    total_prospects_contacted = 0
    total_emails_sent = 0
    
    db_manager = get_db_manager()
    
    # For All Time, calculate from database with actual date range
    if date_range['label'] == 'All Time':
        # Try to get workspace stats from API first
        workspace_stats = fetch_workspace_stats_from_api(start_date, end_date)
        if workspace_stats:
            total_unique_replies = workspace_stats.get('unique_replies_per_contact', 0)
            total_interested = workspace_stats.get('interested', 0)
            total_prospects_contacted = workspace_stats.get('total_leads_contacted', 0)
            total_emails_sent = workspace_stats.get('emails_sent', 0)
        else:
            # Fallback to database calculation
            _, _, total_unique_replies, total_interested = calculate_metrics_from_replies(db_manager, start_date, end_date)
            # Calculate contacted prospects from campaign data
            for campaign in campaigns_list:
                total_prospects_contacted += campaign.get('total_leads_contacted', 0)
                total_emails_sent += campaign.get('emails_sent', 0)
    else:
        # For specific date ranges, try to get workspace stats from API first
        workspace_stats = fetch_workspace_stats_from_api(start_date, end_date)
        if workspace_stats:
            total_unique_replies = workspace_stats.get('unique_replies_per_contact', 0)
            total_interested = workspace_stats.get('interested', 0)
            total_prospects_contacted = workspace_stats.get('total_leads_contacted', 0)
            total_emails_sent = workspace_stats.get('emails_sent', 0)
        else:
            # Fallback to individual campaign API calls
            try:
                # Try to fetch real-time data from EmailBison API for the date range
                real_data = fetch_realtime_metrics_from_api(start_date, end_date)
                if real_data:
                    total_prospects_contacted = real_data.get('prospects_contacted', 0)
                    total_emails_sent = real_data.get('emails_sent', 0)
                    # Still calculate replies from database even when using real-time data
                    _, _, total_unique_replies, total_interested = calculate_metrics_from_replies(db_manager, start_date, end_date)
                else:
                    # Fallback to database calculation - get contacted from campaigns
                    _, _, total_unique_replies, total_interested = calculate_metrics_from_replies(db_manager, start_date, end_date)
                    # Calculate contacted prospects from campaign data
                    for campaign in campaigns_list:
                        total_prospects_contacted += campaign.get('total_leads_contacted', 0)
                        total_emails_sent += campaign.get('emails_sent', 0)
            except Exception as e:
                print(f"Error fetching real-time data: {e}")
                # Fallback to database calculation - get contacted from campaigns
                _, _, total_unique_replies, total_interested = calculate_metrics_from_replies(db_manager, start_date, end_date)
                # Calculate contacted prospects from campaign data
                for campaign in campaigns_list:
                    total_prospects_contacted += campaign.get('total_leads_contacted', 0)
                    total_emails_sent += campaign.get('emails_sent', 0)
    
    # Calculate rates
    reply_rate = (total_unique_replies / total_prospects_contacted * 100) if total_prospects_contacted > 0 else 0
    positive_rate = (total_interested / total_unique_replies * 100) if total_unique_replies > 0 else 0
    
    return {
        'total_leads': total_interested,
        'reply_rate': round(reply_rate, 1),
        'reply_count': total_unique_replies,
        'positive_rate': round(positive_rate, 1),
        'prospects_contacted': total_prospects_contacted,
        'emails_sent': total_emails_sent
    }

def fetch_workspace_line_chart_from_api(start_date, end_date):
    """Fetch workspace line chart data from EmailBison API for specific date range"""
    try:
        print(f"Fetching workspace line chart data from Bison API for {start_date} to {end_date}")
        
        # Use the line chart stats endpoint
        url = f'{EMAILBISON_DOMAIN}/api/workspaces/v1.1/line-area-chart-stats'
        params = {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        }
        
        response = requests.get(url, headers=EMAILBISON_HEADERS, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Extract the chart data from the response
        chart_data = data.get('data', [])
        
        # Find replies and interested data from the chart data
        replies_data = []
        interested_data = []
        
        for item in chart_data:
            label = item.get('label', '')
            dates = item.get('dates', [])
            
            if label == 'Replied':
                replies_data = dates
            elif label == 'Interested':
                interested_data = dates
        
        print(f"Line chart data from Bison API: {len(replies_data)} reply days, {len(interested_data)} interested days")
        
        return {
            'replies': replies_data,
            'interested': interested_data
        }
        
    except Exception as e:
        print(f"Error fetching workspace line chart data: {e}")
        return None

def fetch_workspace_stats_from_api(start_date, end_date):
    """Fetch workspace stats from EmailBison API for specific date range"""
    try:
        print(f"Fetching workspace stats from Bison API for {start_date} to {end_date}")
        
        # Use the workspace stats endpoint
        url = f'{EMAILBISON_DOMAIN}/api/workspaces/v1.1/stats'
        params = {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        }
        
        response = requests.get(url, headers=EMAILBISON_HEADERS, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Extract the stats from the response
        stats = data.get('data', {})
        unique_replies_per_contact = stats.get('unique_replies_per_contact', 0)
        interested = stats.get('interested', 0)
        total_leads_contacted = stats.get('total_leads_contacted', 0)
        emails_sent = stats.get('emails_sent', 0)
        
        print(f"Workspace stats from Bison API: {unique_replies_per_contact} unique replies, {interested} interested, {total_leads_contacted} contacted, {emails_sent} emails sent")
        
        return {
            'unique_replies_per_contact': unique_replies_per_contact,
            'interested': interested,
            'total_leads_contacted': total_leads_contacted,
            'emails_sent': emails_sent
        }
        
    except Exception as e:
        print(f"Error fetching workspace stats: {e}")
        return None

def fetch_realtime_metrics_from_api(start_date, end_date):
    """Fetch real-time metrics from EmailBison API for specific date range"""
    try:
        print(f"Fetching real-time metrics from Bison API for {start_date} to {end_date}")
        
        # Get all campaigns from database
        db_manager = get_db_manager()
        campaigns = db_manager.execute_query("SELECT id FROM campaigns")
        campaign_ids = [row[0] for row in campaigns]
        
        total_prospects_contacted = 0
        total_emails_sent = 0
        
        # Fetch stats for each campaign in the date range
        for campaign_id in campaign_ids:
            try:
                # Try to fetch campaign stats for the specific date range
                stats = fetch_campaign_stats_for_period(campaign_id, start_date, end_date)
                if stats:
                    total_prospects_contacted += stats.get('total_leads_contacted', 0)
                    total_emails_sent += stats.get('emails_sent', 0)
                    print(f"  Campaign {campaign_id}: {stats.get('total_leads_contacted', 0)} contacted, {stats.get('emails_sent', 0)} emails sent")
            except Exception as e:
                print(f"  Error fetching stats for campaign {campaign_id}: {e}")
                continue
        
        print(f"Total from Bison API: {total_prospects_contacted} contacted, {total_emails_sent} emails sent")
        
        return {
            'prospects_contacted': total_prospects_contacted,
            'emails_sent': total_emails_sent,
            'unique_replies': 0,  # Will be calculated from replies
            'interested': 0       # Will be calculated from replies
        }
        
    except Exception as e:
        print(f"Error fetching real-time metrics: {e}")
        return None

def calculate_metrics_from_replies(db_manager, start_date, end_date):
    """Calculate metrics from replies data as fallback"""
    # Get replies data for the timeframe
    all_replies = db_manager.execute_query("""
        SELECT lead_id, interested, campaign_id
        FROM replies 
        WHERE DATE(LEFT(date_received, 10)) BETWEEN %s AND %s
        AND automated_reply = false
    """, (start_date.isoformat(), end_date.isoformat()))
    
    unique_leads = set()
    interested_leads = set()
    
    for reply in all_replies:
        lead_id = reply[0]
        is_interested = reply[1]
        campaign_id = reply[2]
        
        unique_leads.add(lead_id)
        if is_interested:
            interested_leads.add(lead_id)
    
    total_unique_replies = len(unique_leads)
    total_interested = len(interested_leads)
    
    # For contacted prospects and emails sent, we need to get this from campaign data
    # since replies data only shows people who replied, not all contacted
    total_prospects_contacted = 0  # Will be calculated from campaign data
    total_emails_sent = len(all_replies) if all_replies else 0  # Total replies received
    
    return total_prospects_contacted, total_emails_sent, total_unique_replies, total_interested

def generate_chart_data_from_db(leads_data, campaigns_data, date_range):
    """Generate chart data from database"""
    leads_list = leads_data.get('leads', [])
    campaigns_list = campaigns_data.get('campaigns', [])
    
    # For "All Time", use the full date range from database
    if date_range['label'] == 'All Time':
        # Get the actual date range from the database
        db_manager = get_db_manager()
        date_range_result = db_manager.execute_query("""
            SELECT MIN(DATE(LEFT(date_received, 10))) as min_date, 
                   MAX(DATE(LEFT(date_received, 10))) as max_date
            FROM replies 
            WHERE automated_reply = false
        """)
        
        if date_range_result and len(date_range_result) > 0 and date_range_result[0] and len(date_range_result[0]) > 0 and date_range_result[0][0]:
            try:
                # Handle both string and non-string formats
                min_val = date_range_result[0][0]
                max_val = date_range_result[0][1] if len(date_range_result[0]) > 1 else min_val
                
                if isinstance(min_val, str):
                    min_date = datetime.strptime(min_val, '%Y-%m-%d').date()
                else:
                    min_date = min_val if hasattr(min_val, 'year') else datetime.now().date()
                
                if isinstance(max_val, str):
                    max_date = datetime.strptime(max_val, '%Y-%m-%d').date()
                else:
                    max_date = max_val if hasattr(max_val, 'year') else datetime.now().date()
                
                start_date = min_date
                end_date = max_date
            except:
                # Fallback to last 90 days if parsing fails
                from datetime import timedelta
                start_date = max(date_range['start'], (datetime.now() - timedelta(days=90)).date())
                end_date = date_range['end']
        else:
            # Fallback to last 90 days if no data
            from datetime import timedelta
            start_date = max(date_range['start'], (datetime.now() - timedelta(days=90)).date())
            end_date = date_range['end']
    else:
        start_date = date_range['start']
        end_date = date_range['end']
    
    # 1. Replies Over Time
    replies_over_time = generate_replies_over_time_from_db(campaigns_list, {'start': start_date, 'end': end_date})
    
    # 2. Campaign Breakdown
    campaign_breakdown = generate_campaign_breakdown_from_db(campaigns_list, {'start': start_date, 'end': end_date})
    
    # 3. Reply Status Breakdown
    reply_status = generate_reply_status_breakdown_from_db(campaigns_list, {'start': start_date, 'end': end_date})
    
    # 4. Positive Leads by Title
    leads_by_title = generate_leads_by_title_from_db(leads_list, campaigns_list, {'start': start_date, 'end': end_date})
    
    # 5. Positive Leads by Location
    leads_by_location = generate_leads_by_location_from_db(leads_list, campaigns_list, {'start': start_date, 'end': end_date})
    
    # 6. Campaign Performance - Positive Replies vs Contacted
    campaign_performance = generate_campaign_performance_from_db(campaigns_list, {'start': start_date, 'end': end_date})
    
    # 7. Map Locations Data
    map_locations = generate_map_locations_from_db(leads_list, campaigns_list, {'start': start_date, 'end': end_date})
    
    return {
        'replies_over_time': replies_over_time,
        'campaign_breakdown': campaign_breakdown,
        'reply_status': reply_status,
        'leads_by_title': leads_by_title,
        'leads_by_location': leads_by_location,
        'campaign_performance': campaign_performance,
        'map_locations': map_locations
    }

def generate_replies_over_time_from_db(campaigns_list, date_range):
    """Generate replies over time chart data from EmailBison API"""
    start_date = date_range['start']
    end_date = date_range['end']
    
    # Try to get line chart data from EmailBison API first
    line_chart_data = fetch_workspace_line_chart_from_api(start_date, end_date)
    if line_chart_data:
        # Process API data into the expected format
        replies_data = line_chart_data.get('replies', [])
        interested_data = line_chart_data.get('interested', [])
        
        # Convert API data to date-value dictionaries
        replies_by_date = {}
        interested_by_date = {}
        
        for reply_entry in replies_data:
            if len(reply_entry) >= 2:
                date_str = reply_entry[0]
                count = reply_entry[1]
                try:
                    reply_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    replies_by_date[reply_date] = count
                except:
                    pass
        
        for interested_entry in interested_data:
            if len(interested_entry) >= 2:
                date_str = interested_entry[0]
                count = interested_entry[1]
                try:
                    interested_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    interested_by_date[interested_date] = count
                except:
                    pass
        
        # Create date buckets for the full range
        all_replies_counts = {}
        interested_counts = {}
        current = start_date
        while current <= end_date:
            all_replies_counts[current] = replies_by_date.get(current, 0)
            interested_counts[current] = interested_by_date.get(current, 0)
            current += timedelta(days=1)
        
        labels = [d.strftime('%b %d') for d in sorted(all_replies_counts.keys())]
        all_values = [all_replies_counts[d] for d in sorted(all_replies_counts.keys())]
        positive_values = [interested_counts[d] for d in sorted(interested_counts.keys())]
        
        return {
            'labels': labels,
            'all_values': all_values,
            'positive_values': positive_values
        }
    
    # Fallback to database calculation if API fails
    print("Falling back to database calculation for replies over time")
    
    # Get replies grouped by date
    db_manager = get_db_manager()
    replies = db_manager.execute_query("""
        SELECT DATE(LEFT(date_received, 10)) as reply_date, lead_id, interested
        FROM replies
        WHERE DATE(LEFT(date_received, 10)) BETWEEN %s AND %s
        AND automated_reply = false
        ORDER BY date_received
    """, (start_date.isoformat(), end_date.isoformat()))
    
    # Group by date and deduplicate by lead
    replies_by_date = {}
    for reply in replies:
        # Handle both date objects (Postgres) and strings (SQLite)
        if isinstance(reply[0], str):
            reply_date = datetime.strptime(reply[0], '%Y-%m-%d').date()
        else:
            reply_date = reply[0]  # Already a date object
        lead_id = reply[1]
        is_interested = reply[2]
        
        if reply_date not in replies_by_date:
            replies_by_date[reply_date] = {'leads': set(), 'interested_leads': set()}
        
        replies_by_date[reply_date]['leads'].add(lead_id)
        if is_interested:
            replies_by_date[reply_date]['interested_leads'].add(lead_id)
    
    # Create date buckets
    all_replies_counts = {}
    interested_counts = {}
    current = start_date
    while current <= end_date:
        all_replies_counts[current] = len(replies_by_date.get(current, {}).get('leads', set()))
        interested_counts[current] = len(replies_by_date.get(current, {}).get('interested_leads', set()))
        current += timedelta(days=1)
    
    labels = [d.strftime('%b %d') for d in sorted(all_replies_counts.keys())]
    all_values = [all_replies_counts[d] for d in sorted(all_replies_counts.keys())]
    positive_values = [interested_counts[d] for d in sorted(interested_counts.keys())]
    
    return {
        'labels': labels,
        'all_values': all_values,
        'positive_values': positive_values
    }

def generate_campaign_breakdown_from_db(campaigns_list, date_range):
    """Generate campaign breakdown pie chart from database - shows only positive replies (leads)"""
    start_date = date_range['start']
    end_date = date_range['end']
    
    # Get campaign positive reply counts for the date range
    db_manager = get_db_manager()
    campaign_replies = db_manager.execute_query("""
        SELECT campaign_id, COUNT(DISTINCT lead_id) as unique_leads
        FROM replies
        WHERE DATE(LEFT(date_received, 10)) BETWEEN %s AND %s
        AND automated_reply = false
        AND interested = true
        GROUP BY campaign_id
    """, (start_date.isoformat(), end_date.isoformat()))
    
    campaign_data = []
    for campaign_reply in campaign_replies:
        campaign_id = campaign_reply[0]
        unique_leads = campaign_reply[1]
        
        # Find campaign name
        campaign_name = f'Campaign {campaign_id}'
        for campaign in campaigns_list:
            if campaign.get('id') == campaign_id:
                campaign_name = campaign.get('name', f'Campaign {campaign_id}')
                break
        
        if unique_leads > 0:
            campaign_data.append((campaign_name, unique_leads))
    
    # Sort by positive lead count
    campaign_data.sort(key=lambda x: x[1], reverse=True)
    
    # Top 5 campaigns + others
    top_5 = campaign_data[:5]
    others_count = sum(c[1] for c in campaign_data[5:])
    
    labels = [name for name, count in top_5]
    values = [count for name, count in top_5]
    
    if others_count > 0:
        labels.append('Others')
        values.append(others_count)
    
    return {'labels': labels, 'values': values}

def generate_reply_status_breakdown_from_db(campaigns_list, date_range):
    """Generate reply status breakdown chart from database"""
    start_date = date_range['start']
    end_date = date_range['end']
    
    # Get unique leads and interested leads for the date range
    db_manager = get_db_manager()
    stats = db_manager.execute_query("""
        SELECT 
            COUNT(DISTINCT lead_id) as total_replied,
            COUNT(DISTINCT CASE WHEN interested = true THEN lead_id END) as total_interested
        FROM replies
        WHERE DATE(LEFT(date_received, 10)) BETWEEN %s AND %s
        AND automated_reply = false
    """, (start_date.isoformat(), end_date.isoformat()))
    
    if stats:
        total_replied = stats[0][0]
        total_interested = stats[0][1]
        non_interested = total_replied - total_interested if total_replied > total_interested else 0
    else:
        total_replied = 0
        total_interested = 0
        non_interested = 0
    
    return {
        'labels': ['Interested', 'Replied (Not Interested)'],
        'values': [total_interested, non_interested]
    }

def generate_leads_by_title_from_db(leads_list, campaigns_list, date_range):
    """Generate positive leads by title breakdown from database"""
    start_date = date_range['start']
    end_date = date_range['end']
    
    # Get interested leads from the date range
    db_manager = get_db_manager()
    interested_leads = db_manager.execute_query("""
        SELECT DISTINCT r.lead_id
        FROM replies r
        WHERE DATE(LEFT(r.date_received, 10)) BETWEEN %s AND %s
        AND r.interested = true
        AND r.automated_reply = false
    """, (start_date.isoformat(), end_date.isoformat()))
    
    lead_ids = [lead[0] for lead in interested_leads]
    
    if not lead_ids:
        return {'labels': [], 'values': []}
    
    # Get titles for these leads
    placeholders = ','.join(['%s' for _ in lead_ids])
    titles = db_manager.execute_query(f"""
        SELECT title, COUNT(*) as count
        FROM leads
        WHERE id IN ({placeholders})
        AND title IS NOT NULL AND title != ''
        GROUP BY title
        ORDER BY count DESC
        LIMIT 10
    """, lead_ids)
    
    labels = [title[0] for title in titles]
    values = [title[1] for title in titles]
    
    return {'labels': labels, 'values': values}

def generate_leads_by_location_from_db(leads_list, campaigns_list, date_range):
    """Generate positive leads by location (company-based) from database"""
    start_date = date_range['start']
    end_date = date_range['end']
    
    # Get interested leads from the date range
    db_manager = get_db_manager()
    interested_leads = db_manager.execute_query("""
        SELECT DISTINCT r.lead_id
        FROM replies r
        WHERE DATE(LEFT(r.date_received, 10)) BETWEEN %s AND %s
        AND r.interested = true
        AND r.automated_reply = false
    """, (start_date.isoformat(), end_date.isoformat()))
    
    lead_ids = [lead[0] for lead in interested_leads]
    
    if not lead_ids:
        return {'labels': [], 'values': []}
    
    # Get companies for these leads
    placeholders = ','.join(['%s' for _ in lead_ids])
    companies = db_manager.execute_query(f"""
        SELECT company, COUNT(*) as count
        FROM leads
        WHERE id IN ({placeholders})
        AND company IS NOT NULL AND company != ''
        GROUP BY company
        ORDER BY count DESC
        LIMIT 10
    """, lead_ids)
    
    labels = [company[0] for company in companies]
    values = [company[1] for company in companies]
    
    return {'labels': labels, 'values': values}

def generate_campaign_performance_from_db(campaigns_list, date_range):
    """Generate campaign performance chart: Positive Rate (Positive Replies / Contacted People)"""
    start_date = date_range['start']
    end_date = date_range['end']
    
    db_manager = get_db_manager()
    
    # Get campaign data with positive replies and contacted counts
    campaign_data = []
    
    for campaign in campaigns_list:
        campaign_id = campaign.get('id')
        campaign_name = campaign.get('name', f'Campaign {campaign_id}')
        
        # Get positive replies count for this campaign in date range
        positive_replies = db_manager.execute_query("""
            SELECT COUNT(*) as positive_count
            FROM replies
            WHERE campaign_id = %s
            AND interested = true
            AND automated_reply = false
            AND DATE(LEFT(date_received, 10)) BETWEEN %s AND %s
        """, (campaign_id, start_date.isoformat(), end_date.isoformat()))
        
        positive_count = positive_replies[0][0] if positive_replies else 0
        
        # Get contacted count from campaign
        contacted_count = campaign.get('total_leads_contacted', 0)
        
        # Calculate positive rate (percentage)
        positive_rate = (positive_count / contacted_count * 100) if contacted_count > 0 else 0
        
        # Only include campaigns with positive replies in the selected timeframe
        if positive_count > 0 and contacted_count > 0:
            campaign_data.append({
                'name': campaign_name,
                'positive': positive_count,
                'contacted': contacted_count,
                'rate': round(positive_rate, 1)
            })
    
    # Sort by positive rate (descending) and take top 10
    campaign_data.sort(key=lambda x: x['rate'], reverse=True)
    campaign_data = campaign_data[:10]
    
    # Prepare data for chart
    labels = [c['name'] for c in campaign_data]
    rates = [c['rate'] for c in campaign_data]
    positive_counts = [c['positive'] for c in campaign_data]
    contacted_counts = [c['contacted'] for c in campaign_data]
    
    return {
        'labels': labels,
        'rates': rates,
        'positive_counts': positive_counts,
        'contacted_counts': contacted_counts
    }

def generate_map_locations_from_db(leads_list, campaigns_list, date_range):
    """Generate state-level aggregated map data with reply counts"""
    start_date = date_range['start']
    end_date = date_range['end']
    
    # US State full names mapping
    state_names = {
        'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California',
        'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware', 'FL': 'Florida', 'GA': 'Georgia',
        'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa',
        'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
        'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri',
        'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey',
        'NM': 'New Mexico', 'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio',
        'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
        'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont',
        'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming',
        'DC': 'District of Columbia'
    }
    
    # Reverse mapping: full name to code
    name_to_code = {name.upper(): code for code, name in state_names.items()}
    
    def normalize_state(state_str):
        """Normalize state string to 2-letter code, return None if not US state"""
        if not state_str:
            return None
        
        # Convert to string if it's not already
        if not isinstance(state_str, str):
            state_str = str(state_str)
        
        state_upper = state_str.strip().upper()
        
        # Already a 2-letter code
        if len(state_upper) == 2 and state_upper in state_names:
            return state_upper
        
        # Full state name
        if state_upper in name_to_code:
            return name_to_code[state_upper]
        
        # Canadian provinces or other non-US locations
        return None
    
    db_manager = get_db_manager()
    
    # Get leads with replies in the date range, including state from custom variable
    leads_with_activity = db_manager.execute_query("""
        SELECT l.state, r.interested
        FROM leads l
        INNER JOIN replies r ON l.id = r.lead_id
        WHERE DATE(LEFT(r.date_received, 10)) BETWEEN %s AND %s
        AND r.automated_reply = false
        AND l.state IS NOT NULL
        AND l.state != ''
    """, (start_date.isoformat(), end_date.isoformat()))
    
    # Aggregate by state
    state_stats = {}
    
    for lead in leads_with_activity:
        raw_state = lead[0]
        interested = bool(lead[1])
        
        # Normalize state (converts full names to codes, filters out non-US)
        state_code = normalize_state(raw_state)
        
        if not state_code:
            continue
        
        # Aggregate counts
        if state_code not in state_stats:
            state_stats[state_code] = {
                'state_code': state_code,
                'state_name': state_names[state_code],
                'total_replies': 0,
                'interested': 0,
                'replied': 0
            }
        
        state_stats[state_code]['total_replies'] += 1
        if interested:
            state_stats[state_code]['interested'] += 1
        else:
            state_stats[state_code]['replied'] += 1
    
    # Convert to list
    return list(state_stats.values())

# Legacy API functions (kept for reference)
def fetch_emailbison_leads(max_pages=5):
    """Fetch leads data from EmailBison API (paginated)"""
    try:
        all_leads = []
        url = f'{EMAILBISON_DOMAIN}/api/leads'
        
        # Fetch first page to get meta info
        response = requests.get(url, headers=EMAILBISON_HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Add first page leads
        if 'data' in data:
            all_leads.extend(data['data'])
        
        # Get metadata for additional pages
        meta = data.get('meta', {})
        total_leads = meta.get('total', 0)
        last_page = min(meta.get('last_page', 1), max_pages)  # Limit pages for performance
        
        # Fetch additional pages
        for page in range(2, last_page + 1):
            response = requests.get(f'{url}?page={page}', headers=EMAILBISON_HEADERS, timeout=10)
            if response.status_code == 200:
                page_data = response.json()
                if 'data' in page_data:
                    all_leads.extend(page_data['data'])
        
        return {'leads': all_leads, 'total': total_leads, 'meta': meta}
    except Exception as e:
        print(f"Error fetching leads: {e}")
        return {'leads': [], 'total': 0, 'meta': {}}

def fetch_emailbison_campaigns():
    """Fetch campaign data from EmailBison API"""
    try:
        url = f'{EMAILBISON_DOMAIN}/api/campaigns'
        response = requests.get(url, headers=EMAILBISON_HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        campaigns = data.get('data', [])
        total = data.get('meta', {}).get('total', 0)
        
        return {'campaigns': campaigns, 'total': total}
    except Exception as e:
        print(f"Error fetching campaigns: {e}")
        return {'campaigns': [], 'total': 0}

def fetch_campaign_stats_for_period(campaign_id, start_date, end_date):
    """Fetch campaign stats for a specific date range"""
    try:
        url = f'{EMAILBISON_DOMAIN}/api/campaigns/{campaign_id}/stats'
        payload = {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d')
        }
        response = requests.post(url, headers=EMAILBISON_HEADERS, json=payload, timeout=10)
        response.raise_for_status()
        return response.json().get('data', {})
    except Exception as e:
        print(f"Error fetching stats for campaign {campaign_id}: {e}")
        return {}

def calculate_metrics(leads_data, campaigns_data, date_range):
    """Calculate dashboard metrics using correct definitions"""
    
    campaigns_list = campaigns_data.get('campaigns', [])
    start_date = date_range['start']
    end_date = date_range['end']
    
    # Initialize counters
    total_interested = 0  # Number of Leads = prospects marked as Interested
    total_unique_replies = 0  # Replies = unique prospects that replied
    total_prospects_contacted = 0  # Prospects Contacted = unique contacted prospects
    total_emails_sent = 0
    
    # For All Time, use campaign totals directly (faster)
    if date_range['label'] == 'All Time':
        for campaign in campaigns_list:
            total_interested += campaign.get('interested', 0)
            total_unique_replies += int(campaign.get('unique_replies', 0))
            total_prospects_contacted += campaign.get('total_leads_contacted', 0)
            total_emails_sent += campaign.get('emails_sent', 0)
    else:
        # For specific date ranges, fetch stats for each campaign
        for campaign in campaigns_list:
            campaign_id = campaign.get('id')
            if campaign_id:
                stats = fetch_campaign_stats_for_period(campaign_id, start_date, end_date)
                if stats:
                    total_interested += stats.get('interested', 0)
                    total_unique_replies += stats.get('unique_replies_per_contact', 0)
                    total_prospects_contacted += stats.get('total_leads_contacted', 0)
                    total_emails_sent += stats.get('emails_sent', 0)
    
    # Calculate rates (moved outside the conditional blocks)
    # Reply Rate = unique replies / contacted prospects
    reply_rate = (total_unique_replies / total_prospects_contacted * 100) if total_prospects_contacted > 0 else 0
    
    # Positive Rate = interested leads / replies
    positive_rate = (total_interested / total_unique_replies * 100) if total_unique_replies > 0 else 0
    
    return {
        'total_leads': total_interested,  # Number of Leads = Interested
        'reply_rate': round(reply_rate, 1),
        'reply_count': total_unique_replies,
        'positive_rate': round(positive_rate, 1),
        'prospects_contacted': total_prospects_contacted,
        'emails_sent': total_emails_sent
    }

def generate_chart_data(leads_data, campaigns_data, date_range):
    """Generate chart data from real EmailBison data with date filtering"""
    
    leads_list = leads_data.get('leads', [])
    campaigns_list = campaigns_data.get('campaigns', [])
    
    start_date = date_range['start']
    end_date = date_range['end']
    
    # 1. Replies Over Time - Get replies from all campaigns
    replies_over_time = generate_replies_over_time(campaigns_list, date_range)
    
    # 2. Campaign Breakdown - Pie chart of replies by campaign
    campaign_breakdown = generate_campaign_breakdown(campaigns_list, date_range)
    
    # 3. Reply Status Breakdown - Interested vs Replied
    reply_status = generate_reply_status_breakdown(campaigns_list, date_range)
    
    # 4. Positive Leads by Title - Top titles of interested leads
    leads_by_title = generate_leads_by_title(leads_list, campaigns_list, date_range)
    
    # 5. Positive Leads by Location - Based on company or custom field
    leads_by_location = generate_leads_by_location(leads_list, campaigns_list, date_range)
    
    return {
        'replies_over_time': replies_over_time,
        'campaign_breakdown': campaign_breakdown,
        'reply_status': reply_status,
        'leads_by_title': leads_by_title,
        'leads_by_location': leads_by_location
    }

def generate_leads_over_time_filtered(leads_data, date_range):
    """Generate leads over time data filtered by date range"""
    labels = []
    values = []
    
    start_date = date_range['start']
    end_date = date_range['end']
    date_counts = {}
    
    # Create date buckets
    current = start_date
    while current <= end_date:
        date_counts[current] = 0
        labels.append(current.strftime('%b %d'))
        current += timedelta(days=1)
    
    # Count leads by date
    for lead in leads_data:
        if 'created_at' in lead:
            try:
                lead_date = datetime.fromisoformat(lead['created_at'].replace('Z', '+00:00')).date()
                if lead_date in date_counts:
                    date_counts[lead_date] += 1
            except:
                pass
    
    values = list(date_counts.values())
    
    # Limit to reasonable number of points for visualization
    if len(labels) > 30:
        # Group by week if more than 30 days
        return group_by_week(date_counts, start_date, end_date)
    
    return {'labels': labels, 'values': values}

def group_by_week(date_counts, start_date, end_date):
    """Group daily data by week for better visualization"""
    labels = []
    values = []
    current_week_start = start_date
    current_week_count = 0
    
    for date, count in sorted(date_counts.items()):
        if (date - current_week_start).days >= 7:
            labels.append(current_week_start.strftime('%b %d'))
            values.append(current_week_count)
            current_week_start = date
            current_week_count = count
        else:
            current_week_count += count
    
    # Add last week
    if current_week_count > 0:
        labels.append(current_week_start.strftime('%b %d'))
        values.append(current_week_count)
    
    return {'labels': labels, 'values': values}

def generate_leads_over_time(leads_data):
    """Generate leads over time data from real leads"""
    labels = []
    values = []
    
    # Create date buckets for last 30 days
    date_counts = {}
    for i in range(30, 0, -1):
        date = datetime.now() - timedelta(days=i)
        date_str = date.strftime('%b %d')
        labels.append(date_str)
        date_counts[date.date()] = 0
    
    # Count leads by date
    if isinstance(leads_data, list):
        for lead in leads_data:
            if 'created_at' in lead:
                try:
                    lead_date = datetime.fromisoformat(lead['created_at'].replace('Z', '+00:00')).date()
                    if lead_date in date_counts:
                        date_counts[lead_date] += 1
                except:
                    pass
    
    values = list(date_counts.values())
    
    # Fallback to sample data if no real data
    if sum(values) == 0:
        values = [random.randint(20, 80) for _ in range(30)]
    
    return {'labels': labels, 'values': values}

def generate_email_performance(campaigns_data):
    """Generate email performance metrics from campaigns"""
    sent = 0
    opened = 0
    replied = 0
    interested = 0
    
    for campaign in campaigns_data:
        sent += campaign.get('emails_sent', 0)
        opened += int(campaign.get('unique_opens', 0))
        replied += campaign.get('unique_replies', 0)
        interested += campaign.get('interested', 0)
    
    # Fallback if no data
    if sent == 0:
        return generate_sample_email_data()
    
    return {
        'labels': ['Sent', 'Opened', 'Replied', 'Interested'],
        'values': [sent, opened, replied, interested]
    }

def generate_conversion_funnel(leads_data):
    """Generate conversion funnel from real data"""
    total_leads = len(leads_data)
    contacted = 0
    engaged = 0  # opened or replied
    responded = 0
    interested = 0
    
    for lead in leads_data:
        stats = lead.get('overall_stats', {})
        
        # Contacted = emails sent to them
        if stats.get('emails_sent', 0) > 0:
            contacted += 1
        
        # Engaged = opened emails
        if stats.get('unique_opens', 0) > 0:
            engaged += 1
        
        # Responded = actually replied
        if stats.get('unique_replies', 0) > 0:
            responded += 1
        
        # Interested = marked as interested in campaign
        for campaign_data in lead.get('lead_campaign_data', []):
            if campaign_data.get('interested'):
                interested += 1
                break
    
    # Fallback if no data
    if total_leads == 0:
        return generate_funnel_data()
    
    return {
        'labels': ['Total Leads', 'Contacted', 'Engaged', 'Responded', 'Interested'],
        'values': [total_leads, contacted, engaged, responded, interested]
    }

def generate_lead_sources(leads_data):
    """Generate lead sources distribution from tags"""
    sources = Counter()
    
    for lead in leads_data:
        # Get source from tags
        tags = lead.get('tags', [])
        if tags:
            # Use first tag as source
            source_name = tags[0].get('name', 'Unknown')
            sources[source_name] += 1
        else:
            sources['Untagged'] += 1
    
    # Fallback if no data
    if not sources:
        return generate_source_data()
    
    # Get top 5 sources
    top_sources = sources.most_common(5)
    
    return {
        'labels': [source[0] for source in top_sources],
        'values': [source[1] for source in top_sources]
    }

def generate_replies_over_time(campaigns_list, date_range):
    """Generate replies over time chart data - Unique Leads by Date"""
    start_date = date_range['start']
    end_date = date_range['end']
    
    # For "All Time", limit to recent data to avoid performance issues
    if date_range['label'] == 'All Time':
        # Limit to last 90 days for All Time
        start_date = max(start_date, (datetime.now() - timedelta(days=90)).date())
    
    # Collect all replies from all campaigns
    all_replies_raw = []
    
    for campaign in campaigns_list:
        campaign_id = campaign.get('id')
        
        try:
            # Fetch all pages of replies for this campaign
            page = 1
            # Reduce max_pages for All Time to improve performance
            max_pages = 5 if date_range['label'] == 'All Time' else 10
            
            while page <= max_pages:
                replies_url = f'{EMAILBISON_DOMAIN}/api/campaigns/{campaign_id}/replies?page={page}&per_page=100'
                if not replies_url.startswith('http'):
                    replies_url = f'https://{replies_url}'
                
                replies_response = requests.get(replies_url, headers=EMAILBISON_HEADERS)
                
                if replies_response.status_code == 200:
                    replies_data = replies_response.json()
                    replies_list = replies_data.get('data', [])
                    
                    if not replies_list:
                        break
                    
                    # Add all replies to collection
                    for reply in replies_list:
                        if reply.get('automated_reply', False):
                            continue
                        
                        date_received = reply.get('date_received', '')
                        is_interested = reply.get('interested', False)
                        lead_id = reply.get('lead_id')
                        
                        if date_received:
                            try:
                                reply_date = datetime.fromisoformat(date_received.replace('Z', '+00:00')).date()
                                if start_date <= reply_date <= end_date:
                                    all_replies_raw.append({
                                        'lead_id': lead_id,
                                        'date': reply_date,
                                        'interested': is_interested
                                    })
                            except:
                                pass
                    
                    # Check pagination
                    meta = replies_data.get('meta', {})
                    if meta.get('current_page', page) >= meta.get('last_page', page):
                        break
                    page += 1
                else:
                    break
        except:
            pass
    
    # Group replies by date first, then deduplicate by lead_id per date
    replies_by_date = {}
    for reply in all_replies_raw:
        date = reply['date']
        if date not in replies_by_date:
            replies_by_date[date] = []
        replies_by_date[date].append(reply)
    
    # For each date, deduplicate by lead_id and keep the LATEST reply per lead
    unique_leads_by_date = {}
    interested_leads_by_date = {}
    
    for date, replies in replies_by_date.items():
        # Sort replies by lead_id, then by interested status (interested first)
        # This ensures we get the latest status for each lead
        latest_reply_per_lead = {}
        
        for reply in replies:
            lead_id = reply['lead_id']
            if lead_id not in latest_reply_per_lead:
                latest_reply_per_lead[lead_id] = reply
            else:
                # Keep the reply with interested=True if available, otherwise keep the latest
                if reply['interested'] or not latest_reply_per_lead[lead_id]['interested']:
                    latest_reply_per_lead[lead_id] = reply
        
        # Count unique leads and interested leads for this date
        unique_leads_by_date[date] = len(latest_reply_per_lead)
        interested_leads_by_date[date] = sum(1 for reply in latest_reply_per_lead.values() if reply['interested'])
    
    # Create date buckets
    all_replies_counts = {}
    interested_counts = {}
    current = start_date
    while current <= end_date:
        all_replies_counts[current] = unique_leads_by_date.get(current, 0)
        interested_counts[current] = interested_leads_by_date.get(current, 0)
        current += timedelta(days=1)
    
    labels = [d.strftime('%b %d') for d in sorted(all_replies_counts.keys())]
    all_values = [all_replies_counts[d] for d in sorted(all_replies_counts.keys())]
    positive_values = [interested_counts[d] for d in sorted(interested_counts.keys())]
    
    # Group by week if more than 30 days
    if len(labels) > 30:
        all_grouped = group_by_week(all_replies_counts, start_date, end_date)
        positive_grouped = group_by_week(interested_counts, start_date, end_date)
        return {
            'labels': all_grouped['labels'],
            'all_values': all_grouped['values'],
            'positive_values': positive_grouped['values']
        }
    
    return {
        'labels': labels,
        'all_values': all_values,
        'positive_values': positive_values
    }

def generate_campaign_breakdown(campaigns_list, date_range):
    """Generate campaign breakdown pie chart based on timeframe"""
    start_date = date_range['start']
    end_date = date_range['end']
    
    # For "All Time", limit to recent data to avoid performance issues
    if date_range['label'] == 'All Time':
        start_date = max(start_date, (datetime.now() - timedelta(days=90)).date())
    
    labels = []
    values = []
    
    # Collect campaign data with replies in the date range
    campaign_data = []
    
    for campaign in campaigns_list:
        campaign_id = campaign.get('id')
        campaign_name = campaign.get('name', f'Campaign {campaign_id}')
        
        # Count replies for this campaign within the date range
        campaign_replies = 0
        
        try:
            # Fetch replies for this campaign
            page = 1
            # Reduce max_pages for All Time to improve performance
            max_pages = 2 if date_range['label'] == 'All Time' else 3
            
            while page <= max_pages:
                replies_url = f'{EMAILBISON_DOMAIN}/api/campaigns/{campaign_id}/replies?page={page}&per_page=100'
                if not replies_url.startswith('http'):
                    replies_url = f'https://{replies_url}'
                
                replies_response = requests.get(replies_url, headers=EMAILBISON_HEADERS)
                
                if replies_response.status_code == 200:
                    replies_data = replies_response.json()
                    replies_list = replies_data.get('data', [])
                    
                    if not replies_list:
                        break
                    
                    # Count unique leads who replied in the date range
                    unique_leads = set()
                    
                    for reply in replies_list:
                        if reply.get('automated_reply', False):
                            continue
                        
                        date_received = reply.get('date_received', '')
                        lead_id = reply.get('lead_id')
                        
                        if date_received and lead_id:
                            try:
                                reply_date = datetime.fromisoformat(date_received.replace('Z', '+00:00')).date()
                                if start_date <= reply_date <= end_date:
                                    unique_leads.add(lead_id)
                            except:
                                pass
                    
                    campaign_replies = len(unique_leads)
                    
                    # Check pagination
                    meta = replies_data.get('meta', {})
                    if meta.get('current_page', page) >= meta.get('last_page', page):
                        break
                    page += 1
                else:
                    break
        except:
            pass
        
        if campaign_replies > 0:
            campaign_data.append((campaign_name, campaign_replies))
    
    # Sort by reply count
    campaign_data.sort(key=lambda x: x[1], reverse=True)
    
    # Top 5 campaigns + others
    top_5 = campaign_data[:5]
    others_count = sum(c[1] for c in campaign_data[5:])
    
    for name, count in top_5:
        labels.append(name)
        values.append(count)
    
    if others_count > 0:
        labels.append('Others')
        values.append(others_count)
    
    return {'labels': labels, 'values': values}

def generate_reply_status_breakdown(campaigns_list, date_range):
    """Generate reply status breakdown chart based on timeframe"""
    start_date = date_range['start']
    end_date = date_range['end']
    
    # For "All Time", limit to recent data to avoid performance issues
    if date_range['label'] == 'All Time':
        start_date = max(start_date, (datetime.now() - timedelta(days=90)).date())
    
    total_interested = 0
    total_replied = 0
    
    for campaign in campaigns_list:
        campaign_id = campaign.get('id')
        
        try:
            # Fetch replies for this campaign
            page = 1
            # Reduce max_pages for All Time to improve performance
            max_pages = 2 if date_range['label'] == 'All Time' else 3
            
            while page <= max_pages:
                replies_url = f'{EMAILBISON_DOMAIN}/api/campaigns/{campaign_id}/replies?page={page}&per_page=100'
                if not replies_url.startswith('http'):
                    replies_url = f'https://{replies_url}'
                
                replies_response = requests.get(replies_url, headers=EMAILBISON_HEADERS)
                
                if replies_response.status_code == 200:
                    replies_data = replies_response.json()
                    replies_list = replies_data.get('data', [])
                    
                    if not replies_list:
                        break
                    
                    # Count unique leads and interested leads in the date range
                    unique_leads = set()
                    interested_leads = set()
                    
                    for reply in replies_list:
                        if reply.get('automated_reply', False):
                            continue
                        
                        date_received = reply.get('date_received', '')
                        lead_id = reply.get('lead_id')
                        is_interested = reply.get('interested', False)
                        
                        if date_received and lead_id:
                            try:
                                reply_date = datetime.fromisoformat(date_received.replace('Z', '+00:00')).date()
                                if start_date <= reply_date <= end_date:
                                    unique_leads.add(lead_id)
                                    if is_interested:
                                        interested_leads.add(lead_id)
                            except:
                                pass
                    
                    total_replied += len(unique_leads)
                    total_interested += len(interested_leads)
                    
                    # Check pagination
                    meta = replies_data.get('meta', {})
                    if meta.get('current_page', page) >= meta.get('last_page', page):
                        break
                    page += 1
                else:
                    break
        except:
            pass
    
    non_interested = total_replied - total_interested if total_replied > total_interested else 0
    
    return {
        'labels': ['Interested', 'Replied (Not Interested)'],
        'values': [total_interested, non_interested]
    }

def generate_leads_by_title(leads_list, campaigns_list, date_range):
    """Generate positive leads by title breakdown based on timeframe"""
    start_date = date_range['start']
    end_date = date_range['end']
    
    # For "All Time", limit to recent data to avoid performance issues
    if date_range['label'] == 'All Time':
        start_date = max(start_date, (datetime.now() - timedelta(days=90)).date())
    
    # Collect interested leads from the date range
    interested_leads = []
    
    for campaign in campaigns_list:
        campaign_id = campaign.get('id')
        
        try:
            # Fetch replies for this campaign
            page = 1
            # Reduce max_pages for All Time to improve performance
            max_pages = 2 if date_range['label'] == 'All Time' else 3
            
            while page <= max_pages:
                replies_url = f'{EMAILBISON_DOMAIN}/api/campaigns/{campaign_id}/replies?page={page}&per_page=100'
                if not replies_url.startswith('http'):
                    replies_url = f'https://{replies_url}'
                
                replies_response = requests.get(replies_url, headers=EMAILBISON_HEADERS)
                
                if replies_response.status_code == 200:
                    replies_data = replies_response.json()
                    replies_list = replies_data.get('data', [])
                    
                    if not replies_list:
                        break
                    
                    # Get interested leads from this campaign in the date range
                    for reply in replies_list:
                        if reply.get('automated_reply', False):
                            continue
                        
                        date_received = reply.get('date_received', '')
                        lead_id = reply.get('lead_id')
                        is_interested = reply.get('interested', False)
                        
                        if date_received and lead_id and is_interested:
                            try:
                                reply_date = datetime.fromisoformat(date_received.replace('Z', '+00:00')).date()
                                if start_date <= reply_date <= end_date:
                                    # Find the lead in our leads list
                                    for lead in leads_list:
                                        if lead.get('id') == lead_id:
                                            interested_leads.append(lead)
                                            break
                            except:
                                pass
                    
                    # Check pagination
                    meta = replies_data.get('meta', {})
                    if meta.get('current_page', page) >= meta.get('last_page', page):
                        break
                    page += 1
                else:
                    break
        except:
            pass
    
    # Count by title
    title_counts = {}
    for lead in interested_leads:
        title = lead.get('title', 'No Title')
        if title and title.strip():
            title_counts[title] = title_counts.get(title, 0) + 1
    
    # Sort and get top 10
    sorted_titles = sorted(title_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    labels = [t[0] for t in sorted_titles]
    values = [t[1] for t in sorted_titles]
    
    return {'labels': labels, 'values': values}

def generate_leads_by_location(leads_list, campaigns_list, date_range):
    """Generate positive leads by location (company-based) based on timeframe"""
    start_date = date_range['start']
    end_date = date_range['end']
    
    # For "All Time", limit to recent data to avoid performance issues
    if date_range['label'] == 'All Time':
        start_date = max(start_date, (datetime.now() - timedelta(days=90)).date())
    
    # Collect interested leads from the date range
    interested_leads = []
    
    for campaign in campaigns_list:
        campaign_id = campaign.get('id')
        
        try:
            # Fetch replies for this campaign
            page = 1
            # Reduce max_pages for All Time to improve performance
            max_pages = 2 if date_range['label'] == 'All Time' else 3
            
            while page <= max_pages:
                replies_url = f'{EMAILBISON_DOMAIN}/api/campaigns/{campaign_id}/replies?page={page}&per_page=100'
                if not replies_url.startswith('http'):
                    replies_url = f'https://{replies_url}'
                
                replies_response = requests.get(replies_url, headers=EMAILBISON_HEADERS)
                
                if replies_response.status_code == 200:
                    replies_data = replies_response.json()
                    replies_list = replies_data.get('data', [])
                    
                    if not replies_list:
                        break
                    
                    # Get interested leads from this campaign in the date range
                    for reply in replies_list:
                        if reply.get('automated_reply', False):
                            continue
                        
                        date_received = reply.get('date_received', '')
                        lead_id = reply.get('lead_id')
                        is_interested = reply.get('interested', False)
                        
                        if date_received and lead_id and is_interested:
                            try:
                                reply_date = datetime.fromisoformat(date_received.replace('Z', '+00:00')).date()
                                if start_date <= reply_date <= end_date:
                                    # Find the lead in our leads list
                                    for lead in leads_list:
                                        if lead.get('id') == lead_id:
                                            interested_leads.append(lead)
                                            break
                            except:
                                pass
                    
                    # Check pagination
                    meta = replies_data.get('meta', {})
                    if meta.get('current_page', page) >= meta.get('last_page', page):
                        break
                    page += 1
                else:
                    break
        except:
            pass
    
    # Count by company (as proxy for location)
    # In real implementation, you might want to extract city/state from company or use custom fields
    company_counts = {}
    for lead in interested_leads:
        company = lead.get('company', 'Unknown')
        if company and company.strip():
            company_counts[company] = company_counts.get(company, 0) + 1
    
    # Sort and get top 10
    sorted_companies = sorted(company_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    labels = [c[0] for c in sorted_companies]
    values = [c[1] for c in sorted_companies]
    
    return {'labels': labels, 'values': values}

@app.route('/api/sync-data')
def sync_data():
    """Manual sync endpoint to refresh data from EmailBison API"""
    try:
        # Trigger a manual sync
        data_sync_manager = get_sync_manager()
        data_sync_manager.sync_data()
        
        # Get sync status
        db_manager = get_db_manager()
        sync_status = db_manager.execute_query("SELECT last_sync, sync_in_progress, error_message FROM sync_status WHERE id = 1")
        
        if sync_status:
            last_sync, in_progress, error = sync_status[0]
            return jsonify({
                'success': True,
                'message': 'Data sync completed',
                'last_sync': last_sync,
                'sync_in_progress': bool(in_progress),
                'error': error
            })
        else:
            return jsonify({
                'success': True,
                'message': 'Data sync completed',
                'last_sync': None,
                'sync_in_progress': False,
                'error': None
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

if __name__ == '__main__':
    # Initialize database and start background sync
    print("Initializing database and starting background sync...")
    data_sync_manager = get_sync_manager()
    data_sync_manager.sync_data()  # Initial sync
    print("Starting Flask app...")
    app.run(host='0.0.0.0', port=5000, debug=True)

