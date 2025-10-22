# 🚀 Deployment Guide - LongRun Analytics Dashboard

## Pre-Deployment Checklist

- [x] EmailBison API integration complete
- [x] Real data flowing from `send.longrun.agency`
- [x] Dashboard displaying 10,487+ leads
- [x] All charts rendering correctly
- [x] Requirements.txt configured
- [x] Procfile for production server
- [x] Environment variables documented

## 📦 What's Included

### API Integration
- **Domain**: `send.longrun.agency`
- **API Key**: Configured in `app.py`
- **Endpoints**: `/api/leads`, `/api/campaigns`
- **Data**: 10,487 leads, 13 campaigns, 26,968 emails sent

### Dashboard Features
- ✅ Total Leads Counter
- ✅ New Leads Today
- ✅ Email Performance Metrics
- ✅ Response Rate Tracking
- ✅ Conversion Rate Analytics
- ✅ 30-Day Trend Chart
- ✅ Lead Sources Distribution
- ✅ Email Funnel Visualization
- ✅ Conversion Funnel
- ✅ Recent Activity Feed

## 🌐 Free Hosting Options

### Option 1: Render (Recommended) ⭐

**Pros:**
- 100% free forever
- Auto-deploy from GitHub
- SSL certificates included
- Custom domains supported
- Easy environment variables

**Steps:**
1. Create account at [render.com](https://render.com)
2. Connect GitHub repository
3. Create new Web Service
4. Configuration:
   ```
   Name: longrun-analytics
   Build Command: pip install -r requirements.txt
   Start Command: gunicorn app:app
   ```
5. Add environment variables:
   ```
   EMAILBISON_API_KEY=5|LJwTR33haOeU6bSlBGU08roquoklOlZg3CsNgEMtdd040014
   EMAILBISON_DOMAIN=https://send.longrun.agency
   SECRET_KEY=longrun_prod_secret_2024
   ```
6. Deploy!

**URL Format:** `https://longrun-analytics.onrender.com`

---

### Option 2: Railway

**Pros:**
- $5 free credit/month
- Great performance
- Simple deployment

**Steps:**
1. Sign up at [railway.app](https://railway.app)
2. New Project → Deploy from GitHub
3. Select repository
4. Add environment variables (same as above)
5. Generate domain

---

### Option 3: PythonAnywhere

**Pros:**
- Free tier includes 1 web app
- Good for learning

**Steps:**
1. Sign up at [pythonanywhere.com](https://pythonanywhere.com)
2. Upload files or clone from Git
3. Create new Flask web app
4. Configure WSGI file
5. Set environment variables
6. Reload

---

## 🔧 Environment Variables

Required for production (now using Supabase):

```bash
# Supabase Database
SUPABASE_URL=https://ocoihazbvkyjuexmhpnj.supabase.co
SUPABASE_KEY=sb_secret_LaBpA-IgbOThrRNoNGPBGQ_EpPhp8K9
DATABASE_URL=postgresql://postgres.ocoihazbvkyjuexmhpnj:sb_secret_LaBpA-IgbOThrRNoNGPBGQ_EpPhp8K9@aws-0-us-east-1.pooler.supabase.com:6543/postgres

# EmailBison API
EMAILBISON_API_KEY=5|LJwTR33haOeU6bSlBGU08roquoklOlZg3CsNgEMtdd040014
EMAILBISON_DOMAIN=https://send.longrun.agency

# Flask
FLASK_ENV=production
SECRET_KEY=longrun_prod_secret_2024
```

### ⚡ Database Migration

**This application now uses Supabase (PostgreSQL) instead of SQLite.**

Benefits:
- ✅ Better for production deployment
- ✅ Handles multiple concurrent users
- ✅ Automatic backups
- ✅ Better performance for large datasets
- ✅ No file-based database issues

To migrate your existing SQLite data to Supabase:
```bash
python migrate_to_supabase.py
```

## 📊 Performance Optimization

### Current Settings:
- Fetches 10 pages (150 leads) for dashboard calculations
- Caches lead data to avoid rate limits
- Responsive charts with Chart.js
- Bootstrap 5 for fast rendering

### To Increase Performance:
1. **Adjust pagination** in `app.py`:
   ```python
   leads_data = fetch_emailbison_leads(max_pages=5)  # Reduce from 10
   ```

2. **Add caching** (optional):
   ```bash
   pip install Flask-Caching
   ```

3. **Enable compression**:
   ```python
   from flask_compress import Compress
   Compress(app)
   ```

## 🔒 Security Notes

- ✅ API key configured (stored in environment variables for production)
- ✅ HTTPS enabled by default on all hosting platforms
- ✅ CORS configured appropriately
- ✅ No sensitive data in frontend code

## 📝 Post-Deployment Testing

After deployment, test these URLs:

1. **Homepage**: `https://your-app.onrender.com/`
2. **Dashboard Data API**: `https://your-app.onrender.com/api/dashboard-data`
3. **Recent Activity API**: `https://your-app.onrender.com/api/recent-activity`

Expected responses:
- Homepage: Full dashboard with charts
- Dashboard Data: JSON with metrics and chart_data
- Recent Activity: JSON array of recent leads

## 🐛 Troubleshooting

### Issue: Dashboard shows 0 leads
**Solution**: Check environment variables are set correctly in hosting platform

### Issue: Charts not loading
**Solution**: Check browser console for JavaScript errors, verify CDN links

### Issue: API timeout
**Solution**: Increase timeout in fetch functions or reduce max_pages parameter

### Issue: 500 Internal Server Error
**Solution**: Check application logs in hosting platform dashboard

## 📈 Next Steps

After deployment:

1. ✅ Share dashboard URL with client
2. ⏰ Set up monitoring/uptime checks
3. 📧 Configure email notifications for errors (optional)
4. 🎨 Customize branding (logo, colors, company name)
5. 📊 Add custom metrics based on client needs
6. 🔄 Set up auto-refresh (already configured - 5 min intervals)

## 🆘 Support

For issues with:
- **EmailBison API**: Check [send.longrun.agency](https://send.longrun.agency) dashboard
- **Hosting**: Refer to platform-specific documentation
- **Dashboard Code**: Review `app.py` and check logs

---

**Ready to deploy! 🚀**


