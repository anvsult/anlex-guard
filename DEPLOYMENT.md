# AnLex Guard - Deployment Guide

## Architecture Overview

```
┌──────────────────┐
│  Raspberry Pi    │ ← Hardware sensors/actuators
│  (main.py)       │
└────────┬─────────┘
         │ MQTT (bidirectional)
         │
         ▼
┌──────────────────┐
│  Adafruit IO     │ ← Cloud IoT platform
│  (MQTT + HTTP)   │
└────────┬─────────┘
         │ HTTP (REST API)
         │
         ▼
┌──────────────────┐
│  Flask App       │ ← Web dashboard (cloud_app.py)
│  on Render.com   │
└────────┬─────────┘
         │ SQL inserts (optional)
         │
         ▼
┌──────────────────┐
│  PostgreSQL DB   │ ← Historical data storage
│  on NEON.com     │
└──────────────────┘
```

## Part 1: Raspberry Pi Setup (Hardware Side)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Adafruit IO
Edit `config/config.json`:
```json
{
  "adafruit_io": {
    "username": "your_username",
    "key": "your_adafruit_key",
    "host": "io.adafruit.com",
    "port": 8883,
    "use_tls": true,
    "feeds": {
      "motion": "sensor.motion",
      "temperature": "sensor.temperature",
      "humidity": "sensor.humidity",
      "mode": "mode",
      "alarm": "alarm",
      "event_log": "events",
      "led_control": "actuator.led",
      "buzzer_control": "actuator.buzzer",
      "servo_control": "actuator.servo",
      "stealth_mode": "control.stealth"
    }
  }
}
```

### 3. Run on Raspberry Pi
```bash
python main.py
```

The Raspberry Pi will:
- Read sensors and publish data to Adafruit IO via MQTT
- Subscribe to control feeds and actuate hardware based on commands
- Operate independently of the cloud dashboard

## Part 2: Cloud Deployment (Render.com)

### 1. Prepare Repository
Ensure these files are in your repo:
- `cloud_app.py` - Cloud entry point
- `requirements-cloud.txt` - Cloud dependencies (no hardware libs)
- `Procfile` - Gunicorn configuration
- `api/cloud_routes.py` - Cloud API routes
- `web/templates/` - HTML templates
- `web/static/` - Static assets

### 2. Create Render.com Web Service

1. Go to [Render.com](https://render.com)
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configure:
   - **Name**: `anlex-guard`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements-cloud.txt`
   - **Start Command**: `gunicorn cloud_app:app`

### 3. Set Environment Variables on Render

In your Render service settings, add:
```
ADAFRUIT_IO_USERNAME=your_username
ADAFRUIT_IO_KEY=your_key
```

Optional feed names (if different from defaults):
```
FEED_MOTION=sensor.motion
FEED_TEMPERATURE=sensor.temperature
FEED_HUMIDITY=sensor.humidity
FEED_MODE=mode
FEED_ALARM=alarm
FEED_EVENTS=events
FEED_LED=actuator.led
FEED_BUZZER=actuator.buzzer
FEED_SERVO=actuator.servo
FEED_STEALTH=control.stealth
```

### 4. Deploy
- Render will automatically build and deploy
- Your app will be available at `https://your-app-name.onrender.com`

## Part 3: Database Integration (NEON.com - Optional)

### 1. Create NEON Database
1. Go to [NEON.com](https://neon.tech)
2. Create a new project
3. Copy the connection string

### 2. Add to Environment
On Render.com, add:
```
DATABASE_URL=postgresql://user:pass@host/db
```

### 3. Database Schema
```sql
CREATE TABLE sensor_readings (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT NOW(),
    sensor_type VARCHAR(50),
    value DECIMAL(10, 2),
    unit VARCHAR(20)
);

CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT NOW(),
    event_type VARCHAR(100),
    details TEXT
);
```

## Testing

### Test Adafruit IO Connection
```bash
curl https://your-app.onrender.com/api/health
```

### Test Control
```bash
# Arm system
curl -X POST https://your-app.onrender.com/api/arm

# Control LED
curl -X POST https://your-app.onrender.com/api/control/led \
  -H "Content-Type: application/json" \
  -d '{"action": "blink-fast"}'
```

### Test Data Retrieval
```bash
# Get status
curl https://your-app.onrender.com/api/status

# Get temperature history
curl "https://your-app.onrender.com/api/history/temperature?start=2024-01-01T00:00:00&end=2024-12-31T23:59:59"
```

## Data Flow

### Sensor Data (Raspberry Pi → Cloud)
1. Raspberry Pi reads sensor → Publishes to Adafruit IO (MQTT)
2. Cloud app fetches from Adafruit IO (HTTP REST API)
3. Frontend displays data

### Control Commands (Cloud → Raspberry Pi)
1. User clicks button in cloud dashboard
2. Cloud app publishes to Adafruit IO (HTTP REST API)
3. Raspberry Pi receives via MQTT subscription
4. Raspberry Pi actuates hardware

## Monitoring

### Adafruit IO Dashboard
- View live data at `https://io.adafruit.com`
- Create custom dashboards with feeds
- Set up alerts and triggers

### Render Logs
```bash
# View logs on Render.com dashboard
# Or use Render CLI
render logs --service anlex-guard --tail
```

## Troubleshooting

### Cloud app can't connect to Adafruit IO
- Check environment variables are set correctly
- Verify Adafruit IO username and key
- Check feed names match configuration

### Raspberry Pi not publishing data
- Check MQTT connection in logs
- Verify `config/config.json` has correct credentials
- Ensure internet connection is stable

### Frontend not updating
- Check browser console for errors
- Verify API endpoints are responding
- Check Adafruit IO has recent data

## Security Notes

- Never commit `.env` or `config/config.json` with real credentials
- Use Render's environment variables for secrets
- Enable HTTPS (automatic on Render.com)
- Consider adding authentication for production use
