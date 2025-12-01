# AnLex Guard - Cloud Deployment Guide

## Architecture

- **Raspberry Pi**: Runs full system with hardware control
- **Render.com**: Hosts web dashboard (read-only, no hardware)
- **Neon.tech**: PostgreSQL database for event logs and history
- **Adafruit IO**: Real-time sensor data via MQTT
- **GitHub**: Code repository with auto-deploy

## Setup Steps

### 1. Neon.tech Database Setup

1. Go to [neon.tech](https://neon.tech) and create account
2. Create a new project: "anlex-guard"
3. Copy the connection string (looks like):
   ```
   postgresql://user:password@host.neon.tech/database?sslmode=require
   ```
4. Save this for later

### 2. GitHub Repository Setup

```bash
# Initialize git repository
cd anlex-guard
git init

# Add all files
git add .
git commit -m "Initial commit: AnLex Guard Security System"

# Create GitHub repository (via web interface)
# Then connect:
git remote add origin https://github.com/yourusername/anlex-guard.git
git branch -M main
git push -u origin main
```

### 3. Render.com Setup

1. Go to [render.com](https://render.com) and sign up
2. Connect your GitHub account
3. Click "New +" → "Web Service"
4. Select your `anlex-guard` repository
5. Configure:
   - **Name**: `anlex-guard-dashboard`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements-web.txt`
   - **Start Command**: `gunicorn web_server:app`
   - **Plan**: Free

6. Add Environment Variables:
   - `ADAFRUIT_IO_USERNAME`: (your username)
   - `ADAFRUIT_IO_KEY`: (your API key)
   - `NEON_DATABASE_URL`: (your Neon connection string)

7. Click "Create Web Service"

8. Get your deploy hook URL:
   - Settings → Deploy Hook
   - Copy the URL

9. Add deploy hook to GitHub:
   - GitHub repo → Settings → Secrets → Actions
   - New secret: `RENDER_DEPLOY_HOOK`
   - Paste the deploy hook URL

### 4. Update Raspberry Pi Configuration

Add to your `.env` file:
```bash
# Neon Database
NEON_DATABASE_URL=postgresql://user:password@host.neon.tech/database?sslmode=require

# Render Dashboard URL (for future integrations)
RENDER_DASHBOARD_URL=https://anlex-guard-dashboard.onrender.com
```

Update `requirements.txt` to include:
```
psycopg2-binary==2.9.9
```

Reinstall dependencies:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### 5. Testing the Setup

#### Test Raspberry Pi → Neon Connection
```bash
python3 << EOF
from services.neon_service import NeonDatabaseService
import os
from dotenv import load_dotenv

load_dotenv()
db = NeonDatabaseService(os.getenv('NEON_DATABASE_URL'))
db.log_event('TEST', 'Testing connection from Pi', 'disarmed')
events = db.get_recent_events(limit=5)
print("Recent events:", events)
EOF
```

#### Test Render Dashboard
1. Visit: `https://anlex-guard-dashboard.onrender.com`
2. Should see your dashboard
3. Data will be read-only (no arm/disarm buttons work)
4. Charts should show data from Adafruit IO

### 6. Deployment Workflow

**On Raspberry Pi (Local):**
1. Make code changes
2. Test locally: `python main.py`
3. Commit changes: `git add . && git commit -m "Update feature"`
4. Push to GitHub: `git push origin main`

**Automatic Deploy:**
1. GitHub Actions runs tests
2. Render.com automatically deploys new version
3. Dashboard updates in ~2 minutes

**Data Flow:**
```
Raspberry Pi → Adafruit IO (MQTT) ↓
                                    ↓
Raspberry Pi → Neon.tech (SQL)    ↓
                    ↓              ↓
              Render Dashboard ←──┘
```

## Monitoring

### Check Render Logs
```bash
# Via web interface:
# Render Dashboard → Your Service → Logs

# Or use Render CLI:
render logs -s anlex-guard-dashboard --tail
```

### Check Neon Database
```bash
# Connect with psql:
psql $NEON_DATABASE_URL

# Query events:
SELECT * FROM event_logs ORDER BY timestamp DESC LIMIT 10;

# Query system status:
SELECT * FROM system_status ORDER BY timestamp DESC LIMIT 10;
```

### Check Adafruit IO
- Dashboard: https://io.adafruit.com
- View feeds: sensor.motion, sensor.temperature, sensor.humidity
- Check activity logs

## Troubleshooting

### Render Deploy Fails
- Check build logs in Render dashboard
- Verify `requirements-web.txt` has no Raspberry Pi dependencies
- Ensure environment variables are set

### Database Connection Issues
- Verify Neon connection string is correct
- Check Neon dashboard for connection limits (free tier: 100 concurrent)
- Ensure SSL mode is included in connection string

### Adafruit IO Not Updating
- Check MQTT connection on Raspberry Pi
- Verify API key hasn't expired
- Check rate limits (30 data points/minute on free tier)

## Cost Breakdown

- **Render.com**: Free tier (750 hours/month)
- **Neon.tech**: Free tier (3GB storage)
- **Adafruit IO**: Free tier (30 data points/minute)
- **GitHub**: Free for public repos
- **Total**: $0/month for basic usage

## Upgrading

### When to Upgrade

**Render.com ($7/month):**
- Need custom domain
- Require faster response times
- More than 750 hours/month uptime

**Neon.tech ($19/month):**
- Need more than 3GB storage
- Require more concurrent connections
- Want automated backups

**Adafruit IO Plus ($10/month):**
- Need more than 30 data points/minute
- Require unlimited feeds
- Want no rate limits
