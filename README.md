# AnLex Guard - Cloud Security System

Home security system with cloud dashboard deployment.

> **🌟 NEW**: Full cloud deployment support with Adafruit IO MQTT integration for remote actuator control from Render.com!

## Architecture

- **Raspberry Pi**: Runs hardware sensors/actuators, communicates with Adafruit IO via MQTT
- **Adafruit IO**: Cloud IoT platform for data sync and device control (MQTT for real-time bidirectional communication)
- **Flask App (Cloud)**: Web dashboard deployed on Render.com, controls hardware via Adafruit IO feeds
- **NEON Database** (optional): PostgreSQL for historical data storage

### How It Works
```
Dashboard (Render.com) → Adafruit IO MQTT → Raspberry Pi → Hardware
      ↑                                                          ↓
      └────────────── Status Updates ──────────────────────────┘
```

All actuator controls (LED, Buzzer, Servo, Arm/Disarm) are sent through Adafruit IO feeds, enabling remote control of the Raspberry Pi hardware from anywhere in the world.

## Quick Start

### For Raspberry Pi (Hardware)
```bash
# Install dependencies
pip install -r requirements.txt

# Configure Adafruit IO credentials in config/config.json
# Run the system
python main.py
```

### For Cloud Deployment (Render.com)
See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.

**Quick deploy:**
1. Push code to GitHub
2. Connect to Render.com
3. Set environment variables (ADAFRUIT_IO_USERNAME, ADAFRUIT_IO_KEY)
4. Deploy!

## Features

- 🌡️ **Environmental Monitoring**: Temperature and humidity tracking via DHT sensor
- 🚨 **Motion Detection**: PIR sensor with configurable alarm system
- 🔒 **Smart Lock**: Servo-controlled locking mechanism
- 📸 **Surveillance**: Camera integration for photo capture (Raspberry Pi only)
- 🌐 **Cloud Dashboard**: Access system from anywhere via web interface
- 📊 **Historical Data**: Charts and analytics via Adafruit IO
- 🔔 **Alerts**: Email notifications via Brevo
- 🎚️ **Remote Control**: LED, buzzer, servo control via Adafruit IO MQTT feeds
- 🔐 **RFID Access**: Arm/disarm system using authorized RFID tags
- 🤫 **Stealth Mode**: Silent operation with LED indicators disabled
- 📡 **Bidirectional Control**: Control from cloud dashboard OR local RFID tags

## File Structure

```
anlex-guard/
├── main.py                 # Raspberry Pi entry point (hardware)
├── cloud_app.py           # Cloud deployment entry point
├── requirements.txt       # Raspberry Pi dependencies
├── requirements-cloud.txt # Cloud deployment dependencies
├── Procfile              # Render.com configuration
├── DEPLOYMENT.md         # Deployment guide
├── api/
│   ├── routes.py         # Local API routes (with hardware)
│   └── cloud_routes.py   # Cloud API routes (HTTP only)
├── app/
│   ├── state_machine.py  # Core security logic
│   └── config.py         # Configuration management
├── hardware/
│   ├── sensors.py        # Sensor interfaces
│   ├── actuators.py      # Actuator controls
│   └── camera.py         # Camera module
├── services/
│   ├── adafruit_service.py  # Adafruit IO integration
│   ├── email_service.py     # Brevo email service
│   └── storage_service.py   # Image storage
└── web/
    ├── templates/        # HTML templates
    └── static/          # CSS, JS, images
```

## Configuration

### Raspberry Pi (config/config.json)
```json
{
  "adafruit_io": {
    "username": "your_username",
    "key": "your_key",
    "feeds": { ... }
  },
  "email": { ... },
  "pins": { ... }
}
```

### Cloud (.env on Render.com)
```
ADAFRUIT_IO_USERNAME=your_username
ADAFRUIT_IO_KEY=your_key
```

## API Endpoints

### Control
- `POST /api/arm` - Arm system
- `POST /api/disarm` - Disarm system
- `POST /api/stealth` - Toggle stealth mode
- `POST /api/control/led` - Control LED
- `POST /api/control/buzzer` - Control buzzer
- `POST /api/control/servo` - Lock/unlock servo

### Data
- `GET /api/status` - Current system status
- `GET /api/logs` - Event logs
- `GET /api/history/temperature` - Temperature history
- `GET /api/history/humidity` - Humidity history
- `GET /api/history/motion` - Motion detection history

## Development

### Local Testing (without hardware)
```bash
pip install -r requirements-cloud.txt
export ADAFRUIT_IO_USERNAME=your_username
export ADAFRUIT_IO_KEY=your_key
python cloud_app.py
```

### With Hardware (Raspberry Pi)
```bash
pip install -r requirements.txt
python main.py
```

## Deployment

See **[CLOUD_DEPLOYMENT.md](CLOUD_DEPLOYMENT.md)** for complete guide on:
- Cloud deployment architecture with Adafruit IO MQTT
- Setting up Raspberry Pi with hardware
- Deploying dashboard to Render.com
- Configuring Adafruit IO feeds for actuator control
- Environment variables and security
- Troubleshooting common issues

Also see [DEPLOYMENT.md](DEPLOYMENT.md) for additional deployment options including:
- NEON.com database integration
- Alternative cloud platforms
- Advanced configuration

## License

MIT

## Team

See [web/templates/about.html](web/templates/about.html) for team information.
