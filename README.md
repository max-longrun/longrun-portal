# LeadGen Analytics Dashboard

A modern, responsive analytics dashboard for lead generation agencies built with Flask, Bootstrap, and Chart.js. This dashboard integrates with EmailBison API to visualize lead generation metrics and campaign performance.

**✅ Currently connected to `send.longrun.agency` with 10,487+ leads tracked!**

## 🚀 Quick Deploy to Production

The fastest way to deploy for free:

1. **Push to GitHub** (if not already done):
   ```bash
   git init
   git add .
   git commit -m "Initial commit - LeadGen Analytics Dashboard"
   git branch -M main
   git remote add origin YOUR_GITHUB_REPO_URL
   git push -u origin main
   ```

2. **Deploy to Render** (100% Free):
   - Go to [render.com](https://render.com) and sign up
   - Click "New +" → "Web Service"
   - Connect your GitHub repo
   - Settings:
     - **Name**: `longrun-analytics`
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `gunicorn app:app`
   - Add Environment Variables:
     - `EMAILBISON_API_KEY` = `5|LJwTR33haOeU6bSlBGU08roquoklOlZg3CsNgEMtdd040014`
     - `EMAILBISON_DOMAIN` = `https://send.longrun.agency`
     - `SECRET_KEY` = `longrun_prod_secret_2024`
   - Click "Create Web Service"
   - Done! Your dashboard will be live in ~3 minutes

## 🚀 Features

- **Real-time Analytics**: Track leads, response rates, and conversions
- **Interactive Charts**: Visualize data with Chart.js (line, bar, pie, and funnel charts)
- **Responsive Design**: Built with Bootstrap 5 for mobile-friendly experience
- **EmailBison Integration**: Ready to connect with EmailBison API for data scraping
- **Modern UI**: Clean, professional interface with gradient cards and smooth animations

## 📋 Prerequisites

- Python 3.11 or higher
- EmailBison API key (sign up at [EmailBison](https://emailbison.com))

## 🛠️ Installation & Setup

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd LongRun_Reports
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the example environment file and add your credentials:

```bash
cp .env.example .env
```

Edit `.env` and add your EmailBison API key:

```
EMAILBISON_API_KEY=your_actual_api_key_here
SECRET_KEY=your_random_secret_key_here
```

### 5. Run Locally

```bash
python app.py
```

Visit `http://localhost:5000` in your browser.

## 🌐 Free Hosting Options

### Option 1: Render (Recommended ⭐)

Render offers a free tier that's perfect for Flask applications.

#### Steps to Deploy on Render:

1. **Create a Render Account**
   - Go to [Render.com](https://render.com)
   - Sign up with GitHub (recommended)

2. **Push Your Code to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin <your-github-repo-url>
   git push -u origin main
   ```

3. **Create New Web Service on Render**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Configure the service:
     - **Name**: `leadgen-analytics`
     - **Environment**: `Python 3`
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `gunicorn app:app`
     - **Plan**: `Free`

4. **Add Environment Variables**
   - In Render dashboard, go to "Environment"
   - Add your variables:
     - `EMAILBISON_API_KEY`: your API key
     - `SECRET_KEY`: random secret key

5. **Deploy**
   - Click "Create Web Service"
   - Wait for deployment (2-3 minutes)
   - Your app will be live at `https://your-app-name.onrender.com`

**Note**: Free tier apps on Render spin down after 15 minutes of inactivity. First request may take 30-60 seconds.

---

### Option 2: Railway

Railway offers $5 free credit per month.

#### Steps to Deploy on Railway:

1. **Create Railway Account**
   - Go to [Railway.app](https://railway.app)
   - Sign up with GitHub

2. **Deploy from GitHub**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository

3. **Configure**
   - Railway auto-detects Python
   - Add environment variables in the "Variables" tab:
     - `EMAILBISON_API_KEY`
     - `SECRET_KEY`

4. **Generate Domain**
   - Go to "Settings" → "Generate Domain"
   - Your app will be live at the generated URL

---

### Option 3: PythonAnywhere

Free tier includes 1 web app.

#### Steps to Deploy on PythonAnywhere:

1. **Create Account**
   - Go to [PythonAnywhere.com](https://www.pythonanywhere.com)
   - Sign up for free Beginner account

2. **Upload Your Code**
   - Go to "Files" tab
   - Upload your project files or clone from GitHub

3. **Create Web App**
   - Go to "Web" tab → "Add a new web app"
   - Choose "Flask" and Python 3.10
   - Set working directory to your project folder

4. **Configure WSGI File**
   - Edit the WSGI configuration file:
   ```python
   import sys
   path = '/home/yourusername/LongRun_Reports'
   if path not in sys.path:
       sys.path.append(path)
   
   from app import app as application
   ```

5. **Set Environment Variables**
   - In web app settings, add environment variables

6. **Reload**
   - Click "Reload" button
   - Visit `yourusername.pythonanywhere.com`

---

### Option 4: Vercel (with Serverless)

Vercel is great for static sites but can host Flask with serverless functions.

#### Steps to Deploy on Vercel:

1. **Install Vercel CLI**
   ```bash
   npm install -g vercel
   ```

2. **Create `vercel.json`** (already included in project):
   ```json
   {
     "builds": [
       {"src": "app.py", "use": "@vercel/python"}
     ],
     "routes": [
       {"src": "/(.*)", "dest": "app.py"}
     ]
   }
   ```

3. **Deploy**
   ```bash
   vercel
   ```

4. **Add Environment Variables**
   - In Vercel dashboard → Settings → Environment Variables
   - Add `EMAILBISON_API_KEY` and `SECRET_KEY`

---

## 🔌 EmailBison API Integration

✅ **ALREADY CONFIGURED** with your EmailBison instance!

The dashboard is connected to:
- **Domain**: `send.longrun.agency`
- **Total Leads**: 10,487
- **Campaigns**: 13 active campaigns
- **Emails Sent**: 26,968+

### API Endpoints Used:
- `/api/leads` - Fetches lead data (paginated, 15 per page)
- `/api/campaigns` - Fetches campaign performance data

### Current Metrics Being Tracked:
- ✓ Total leads count
- ✓ New leads today
- ✓ Emails sent across all campaigns
- ✓ Response rate (unique replies)
- ✓ Conversion rate (interested leads)
- ✓ Lead sources (from tags)
- ✓ 30-day lead trends
- ✓ Email performance funnel
- ✓ Conversion funnel stages

### To Update API Configuration:
Edit lines 11-17 in `app.py`:
```python
EMAILBISON_API_KEY = '5|LJwTR33haOeU6bSlBGU08roquoklOlZg3CsNgEMtdd040014'
EMAILBISON_DOMAIN = 'https://send.longrun.agency'
```

## 📊 Dashboard Components

### Metric Cards
- Total Leads
- New Leads Today
- Response Rate
- Conversion Rate

### Charts
1. **Leads Over Time**: Line chart showing 30-day trend
2. **Lead Sources**: Doughnut chart showing distribution
3. **Email Performance**: Bar chart for email funnel
4. **Conversion Funnel**: Horizontal bar chart for conversion stages

### Activity Table
Recent lead activity with status indicators

## 🎨 Customization

### Update Branding
- Edit `templates/index.html` - change navbar brand and title
- Edit `static/css/style.css` - modify colors in `:root` variables

### Add New Metrics
1. Update API endpoint in `app.py`
2. Add HTML elements in `templates/index.html`
3. Update JavaScript in `static/js/main.js`

## 🔒 Security Notes

- Never commit `.env` file to Git
- Use environment variables for all sensitive data
- Generate a strong SECRET_KEY for production
- Enable HTTPS in production (automatically handled by hosting providers)

## 📝 License

This project is open source and available under the MIT License.

## 🤝 Support

For issues or questions:
- Check EmailBison API documentation
- Review Flask documentation
- Open an issue in this repository

## 🚦 Quick Start Checklist

- [ ] Install Python 3.11+
- [ ] Create virtual environment
- [ ] Install dependencies (`pip install -r requirements.txt`)
- [ ] Get EmailBison API key
- [ ] Create `.env` file with credentials
- [ ] Test locally (`python app.py`)
- [ ] Choose hosting provider
- [ ] Deploy to production
- [ ] Configure environment variables on hosting platform
- [ ] Test production deployment
- [ ] Customize for your client

---

**Built with ❤️ for Lead Generation Agencies**

