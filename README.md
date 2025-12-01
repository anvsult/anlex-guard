# AnLex Guard

Raspberry Pi home security system with motion detection, RFID access control, and environmental monitoring.

## Features

- Motion detection with PIR sensor
- RFID-based access control
- Temperature and humidity monitoring
- USB camera with photo capture
- Web dashboard for monitoring and control
- Adafruit IO cloud integration
- Email notifications

## Hardware

- PIR Motion Sensor (GPIO 17)
- DHT11 Temperature/Humidity Sensor (GPIO 4)
- MFRC522 RFID Reader (SPI)
- USB Camera
- LED Indicator (GPIO 27)
- Buzzer (GPIO 13)
- Servo Motor (GPIO 18)

## Installation

### 1. System Setup

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv
sudo raspi-config  # Enable SPI for RFID
sudo reboot
```

### 2. Install Dependencies

```bash
git clone https://github.com/yourusername/anlex-guard.git
cd anlex-guard
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configuration

Create `.env` file with:
```
ADAFRUIT_IO_USERNAME=your_username
ADAFRUIT_IO_KEY=your_key
AUTHORIZED_RFID_IDS=comma,separated,ids
BREVO_API_KEY=your_key
EMAIL_FROM=sender@email.com
EMAIL_TO=recipient@email.com
```

## Usage

```bash
source venv/bin/activate
python main.py
```

Access dashboard at `http://<raspberry-pi-ip>:5000`

## License

MIT License
