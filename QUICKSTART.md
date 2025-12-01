# Quick Start Guide

## Cloud Deployment (No Hardware Required)

### 1. Get Adafruit IO Credentials
1. Sign up at [io.adafruit.com](https://io.adafruit.com)
2. Go to "My Key" to get your username and key
3. Create these feeds (or they'll be auto-created):
   - `sensor.motion`
   - `sensor.temperature`
   - `sensor.humidity`
   - `actuator.led`
   - `actuator.buzzer`
   - `actuator.servo`
   - `mode`
   - `control.stealth`
   - `events`

### 2. Deploy to Render.com
1. Fork/clone this repo to your GitHub
2. Go to [render.com](https://render.com) and sign up
3. Click "New +" → "Web Service"
4. Connect your GitHub repo
5. Configure:
   - **Name**: `anlex-guard`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements-cloud.txt`
   - **Start Command**: `gunicorn cloud_app:app`
6. Add environment variables:
   ```
   ADAFRUIT_IO_USERNAME=your_username_here
   ADAFRUIT_IO_KEY=your_key_here
   ```
7. Click "Create Web Service"
8. Wait for deployment (2-3 minutes)
9. Access your dashboard at `https://your-app-name.onrender.com`

### 3. Test Without Hardware
You can test the cloud dashboard by manually publishing data to Adafruit IO:

```python
# Test script - publish_test_data.py
import requests
import time

username = "your_username"
key = "your_key"

def publish(feed, value):
    url = f"https://io.adafruit.com/api/v2/{username}/feeds/{feed}/data"
    headers = {"X-AIO-Key": key}
    data = {"value": value}
    response = requests.post(url, headers=headers, json=data)
    print(f"Published {value} to {feed}: {response.status_code}")

# Simulate sensor data
while True:
    publish("sensor.temperature", "22.5")
    publish("sensor.humidity", "65")
    publish("sensor.motion", "0")
    time.sleep(10)
```

Run this script and watch the cloud dashboard update!

## Raspberry Pi Setup (With Hardware)

### 1. Hardware Connections
- PIR Sensor → GPIO 17
- DHT11 → GPIO 4 (data pin)
- LED → GPIO 27
- Buzzer → GPIO 13
- Servo → GPIO 18
- RFID Reader → SPI pins

### 2. Install on Raspberry Pi
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Clone repo
git clone https://github.com/yourusername/anlex-guard.git
cd anlex-guard

# Install dependencies
pip install -r requirements.txt

# Configure Adafruit IO
nano config/config.json
# Update "username" and "key" under "adafruit_io"

# Run
python main.py
```

### 3. Verify Connection
- Check Adafruit IO dashboard at io.adafruit.com
- You should see data appearing in your feeds
- Try controlling actuators from the cloud dashboard

## Full System Test

Once both Raspberry Pi and Cloud are running:

1. **Test Sensor Flow**: 
   - Wave hand in front of PIR sensor
   - Check cloud dashboard for motion detection
   - View temperature/humidity readings

2. **Test Control Flow**:
   - Click "Test LED" in cloud dashboard
   - Verify LED blinks on Raspberry Pi
   - Try buzzer and servo controls

3. **Test Arm/Disarm**:
   - Click "Arm System"
   - Trigger motion sensor
   - Verify alarm activates
   - Click "Disarm System"

## Troubleshooting

### Cloud dashboard shows no data
- Check Adafruit IO feeds have data
- Verify environment variables are set correctly
- Check Render logs for errors

### Raspberry Pi not publishing
- Check internet connection
- Verify Adafruit IO credentials in config.json
- Check logs: `tail -f data/logs/anlex-guard.log`

### Controls not working
- Verify feed names match in both Pi and Cloud configs
- Check Adafruit IO Activity log
- Ensure MQTT connection is active on Pi

## Next Steps

- [ ] Set up email notifications (add Brevo API key)
- [ ] Add NEON database for long-term storage
- [ ] Create custom Adafruit IO dashboards
- [ ] Set up alerts and triggers
- [ ] Add authentication to web dashboard
- [ ] Configure camera (if using on Pi)

## Support

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment guide.
See [ADAFRUIT_INTEGRATION.md](ADAFRUIT_INTEGRATION.md) for architecture details.
