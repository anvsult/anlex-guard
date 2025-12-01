# Cloud Deployment Guide - Adafruit IO Integration

## Overview

The AnLex Guard security system has been configured for cloud deployment on **Render.com** (or similar platforms). All actuator controls (LED, Buzzer, Servo) are now managed through **Adafruit IO MQTT feeds**, enabling remote control of the Raspberry Pi hardware from the cloud-hosted web interface.

## Architecture

```
┌─────────────────────┐         ┌──────────────────────┐         ┌─────────────────────┐
│   Web Browser       │◄───────►│   Render.com         │◄───────►│   Adafruit IO       │
│   (Dashboard)       │  HTTPS  │   (cloud_app.py)     │  MQTT   │   (MQTT Broker)     │
└─────────────────────┘         └──────────────────────┘         └─────────────────────┘
                                                                            ▲
                                                                            │ MQTT
                                                                            │
                                                                   ┌────────▼────────────┐
                                                                   │   Raspberry Pi      │
                                                                   │   (main.py)         │
                                                                   │   Hardware Control  │
                                                                   └─────────────────────┘
```

### Flow:

1. **User** interacts with dashboard on **Render.com** (cloud deployment)
2. **Cloud API** (`cloud_app.py`) publishes commands to **Adafruit IO feeds**
3. **Raspberry Pi** (running `main.py`) subscribes to these feeds via MQTT
4. **Pi** receives commands and controls **physical hardware** (LED, Buzzer, Servo)

## Changes Made

### 1. Cloud Application (`cloud_app.py`)

- Added graceful shutdown handling for Adafruit IO connection
- Established MQTT connection to Adafruit IO on startup
- All actuator control commands now publish to Adafruit IO feeds

### 2. Cloud Routes (`api/cloud_routes.py`)

- Updated `init_cloud_services()` to establish MQTT connection (not just REST API)
- Added `shutdown_cloud_services()` for cleanup
- Enhanced all control endpoints with proper error handling and validation
- Added informative response messages indicating commands are sent to Adafruit IO

#### Control Endpoints:

- `/api/arm` - Arms the system (publishes `"armed"` to `mode` feed)
- `/api/disarm` - Disarms the system (publishes `"disarmed"` to `mode` feed)
- `/api/stealth` - Toggles stealth mode (publishes `"1"` or `"0"` to `stealth_mode` feed)
- `/api/control/led` - Controls LED (publishes actions like `"on"`, `"off"`, `"blink"`, `"blink-fast"`)
- `/api/control/buzzer` - Controls buzzer (publishes actions like `"beep"`, `"siren"`, `"stop"`)
- `/api/control/servo` - Controls servo (publishes `"lock"` or `"unlock"`)

### 3. State Machine (`app/state_machine.py`)

- Added `mode` feed handling to `_handle_adafruit_control()`
- Raspberry Pi can now receive arm/disarm commands from cloud
- Enables bidirectional control: local RFID + cloud dashboard

### 4. Adafruit Service (`services/adafruit_service.py`)

- Added `'mode'` to the list of subscribed control feeds
- Raspberry Pi now listens for mode changes from cloud

## Environment Variables (Render.com)

Set these in your Render.com dashboard:

```bash
# Required
ADAFRUIT_IO_USERNAME=your_username
ADAFRUIT_IO_KEY=your_aio_key

# Optional (override default feed names)
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

## Adafruit IO Feeds Required

Create these feeds in your Adafruit IO account:

### Sensor Data (Published by Pi):

- `sensor.motion` - Motion detection events
- `sensor.temperature` - Temperature readings
- `sensor.humidity` - Humidity readings

### System State (Published by Pi, Read by Cloud):

- `mode` - System mode (armed/disarmed)
- `alarm` - Alarm state
- `events` - Event log

### Control Commands (Published by Cloud, Read by Pi):

- `actuator.led` - LED control commands
- `actuator.buzzer` - Buzzer control commands
- `actuator.servo` - Servo lock/unlock commands
- `control.stealth` - Stealth mode toggle

## Deployment Steps

### 1. Deploy to Render.com

1. Push code to GitHub
2. Create new Web Service on Render.com
3. Connect to your GitHub repository
4. Set build command: `pip install -r requirements-cloud.txt`
5. Set start command: `gunicorn cloud_app:app`
6. Add environment variables (see above)
7. Deploy!

### 2. Configure Raspberry Pi

1. Ensure `main.py` is running on your Raspberry Pi
2. Verify Adafruit IO credentials in `config/config.json`
3. Ensure all feed names match between Pi and cloud
4. Start the service: `python main.py`

### 3. Test the System

1. Open your Render.com URL in a browser
2. Try arming/disarming the system
3. Test LED, buzzer, and servo controls
4. Verify commands appear in Adafruit IO feed logs
5. Confirm Raspberry Pi responds to commands

## How It Works

### Example: Controlling the LED

**From Cloud Dashboard:**

```
User clicks "Turn LED On"
  → POST /api/control/led {"action": "on"}
  → cloud_app.py publishes "on" to Adafruit IO feed "actuator.led"
  → Adafruit IO MQTT broker distributes message
  → Raspberry Pi receives message via subscription
  → state_machine.py calls led.on()
  → Physical LED turns on
```

**Bidirectional Control:**

```
RFID scan on Pi
  → state_machine.py calls arm_system()
  → Publishes "armed" to "mode" feed
  → Cloud dashboard receives update via /api/status
  → Dashboard UI updates to show "Armed" status
```

## Benefits

✅ **Remote Control**: Control hardware from anywhere with internet  
✅ **No Port Forwarding**: No need to expose Raspberry Pi directly to internet  
✅ **Cloud Scalability**: Dashboard hosted on Render.com scales automatically  
✅ **Decoupled Architecture**: Hardware and UI can be updated independently  
✅ **Real-time Updates**: MQTT ensures low-latency command delivery  
✅ **Reliability**: Adafruit IO handles connection management and retry logic

## Limitations

- **Adafruit IO Free Tier**: 30 messages/minute, 30 days data retention
- **Camera Control**: Not available in cloud-only mode (requires direct hardware access)
- **Latency**: Commands go through Adafruit IO (typically 100-500ms delay)

## Troubleshooting

### Cloud app can't connect to Adafruit IO

- Verify `ADAFRUIT_IO_USERNAME` and `ADAFRUIT_IO_KEY` are set correctly
- Check Render.com logs for connection errors
- Ensure firewall allows outbound MQTT (port 8883)

### Raspberry Pi doesn't receive commands

- Verify Pi is connected to Adafruit IO (check logs)
- Ensure feed names match exactly (case-sensitive)
- Check Adafruit IO feed activity logs
- Verify Pi's `config.json` has correct credentials

### Commands are sent but nothing happens

- Check Raspberry Pi logs for errors
- Verify hardware connections (GPIO pins)
- Test hardware directly using local API endpoints
- Ensure state machine is running

## Security Notes

- **Never commit** your Adafruit IO keys to git
- Use environment variables for all credentials
- Consider upgrading to Adafruit IO Plus for better rate limits
- Implement authentication on your Render.com dashboard (future enhancement)

## Next Steps

1. Add authentication to cloud dashboard
2. Implement WebSocket for real-time dashboard updates
3. Add camera image upload to cloud storage (S3, etc.)
4. Create mobile app using Adafruit IO API
5. Set up monitoring and alerting for system health

---

**Created**: December 2025  
**Updated**: For Render.com deployment with Adafruit IO MQTT integration
