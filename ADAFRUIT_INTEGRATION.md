# Adafruit IO Integration - Cloud Architecture

## Overview
The system is split into two independent components that communicate via Adafruit IO:

1. **Raspberry Pi** (Hardware Controller) - Runs `main.py`
2. **Cloud Dashboard** (Render.com) - Runs `cloud_app.py`

## Architecture Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     Raspberry Pi                            │
│  ┌────────────┐         ┌──────────────┐                   │
│  │  Sensors   │────────▶│ state_machine│                   │
│  │  Actuators │◀────────│    (main.py) │                   │
│  └────────────┘         └───────┬──────┘                   │
│                                  │                           │
│                                  │ MQTT (publish/subscribe)  │
└──────────────────────────────────┼───────────────────────────┘
                                   │
                                   ▼
                        ┌──────────────────┐
                        │  Adafruit IO     │
                        │  (Cloud IoT)     │
                        └────────┬─────────┘
                                 │
                                 │ HTTP REST API
                                 ▼
┌─────────────────────────────────────────────────────────────┐
│                    Cloud Dashboard                          │
│  ┌──────────────┐         ┌──────────────┐                 │
│  │  Web Browser │────────▶│  cloud_app.py│                 │
│  │  (User)      │◀────────│  (Render.com)│                 │
│  └──────────────┘         └──────────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

### Sensor Data (Pi → Cloud)
1. Raspberry Pi reads sensors (PIR, DHT, etc.)
2. Publishes to Adafruit IO via MQTT
3. Cloud dashboard fetches via HTTP REST API
4. Frontend displays on charts

### Control Commands (Cloud → Pi)
1. User clicks button in cloud dashboard
2. Cloud app publishes to Adafruit IO via HTTP
3. Raspberry Pi receives via MQTT subscription
4. Pi actuates hardware (LED, buzzer, servo)

## Components

### Raspberry Pi (`main.py`)
- **File**: `main.py`, `app/state_machine.py`, `api/routes.py`
- **Dependencies**: `requirements.txt` (includes hardware libs)
- **Connectivity**: MQTT to Adafruit IO
- **Functions**:
  - Read sensors
  - Control actuators
  - Subscribe to control feeds
  - Publish sensor data

### Cloud Dashboard (`cloud_app.py`)
- **File**: `cloud_app.py`, `api/cloud_routes.py`
- **Dependencies**: `requirements-cloud.txt` (no hardware libs)
- **Connectivity**: HTTP REST to Adafruit IO
- **Functions**:
  - Serve web interface
  - Fetch sensor data from Adafruit IO
  - Publish control commands to Adafruit IO
  - Display historical data

## Adafruit IO Feeds

| Feed Name | Type | Direction | Description |
|-----------|------|-----------|-------------|
| `sensor.motion` | Data | Pi → Cloud | Motion detection events |
| `sensor.temperature` | Data | Pi → Cloud | Temperature readings (°C) |
| `sensor.humidity` | Data | Pi → Cloud | Humidity readings (%) |
| `actuator.led` | Control | Cloud → Pi | LED commands (on/off/blink) |
| `actuator.buzzer` | Control | Cloud → Pi | Buzzer commands (beep/siren) |
| `actuator.servo` | Control | Cloud → Pi | Servo commands (lock/unlock) |
| `mode` | Control | Bidirectional | System mode (armed/disarmed) |
| `control.stealth` | Control | Cloud → Pi | Stealth mode toggle |
| `events` | Data | Pi → Cloud | Event log entries |

## API Endpoints (Cloud)

All endpoints in `api/cloud_routes.py`:

### Status
- `GET /api/status` - Current system status from Adafruit IO
- `GET /api/health` - Health check

### Control
- `POST /api/arm` - Arm system
- `POST /api/disarm` - Disarm system
- `POST /api/stealth` - Toggle stealth mode
- `POST /api/control/led` - Control LED
- `POST /api/control/buzzer` - Control buzzer
- `POST /api/control/servo` - Lock/unlock servo

### Historical Data
- `GET /api/history/temperature?start=...&end=...`
- `GET /api/history/humidity?start=...&end=...`
- `GET /api/history/motion?start=...&end=...`

### Logs
- `GET /api/logs?limit=50`

## Deployment

### Raspberry Pi
```bash
pip install -r requirements.txt
python main.py
```

### Render.com
```bash
# Automatically uses:
# - requirements-cloud.txt
# - cloud_app.py
# - Procfile (gunicorn)
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete instructions.
