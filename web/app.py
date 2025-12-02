import os
import logging
import requests
import json
from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration ---
ADAFRUIT_IO_USERNAME = os.getenv("ADAFRUIT_IO_USERNAME")
ADAFRUIT_IO_KEY = os.getenv("ADAFRUIT_IO_KEY")

# Feed Configuration (Must match keys in your config.json on the Pi)
FEEDS = {
    'mode': 'mode',
    'alarm': 'alarm',
    'stealth': 'control.stealth',       
    'led': 'actuator.led',              
    'buzzer': 'actuator.buzzer',        
    'servo': 'actuator.servo',          
    'motion': 'sensor.motion',
    'temperature': 'sensor.temperature',
    'humidity': 'sensor.humidity',
    'logs': 'events',                   
    'photos': 'photos'
}

# --- Helper Functions ---

def get_headers():
    return {
        "X-AIO-Key": ADAFRUIT_IO_KEY,
        "Content-Type": "application/json"
    }

def aio_get_last(feed_key):
    """Fetch the last value from a specific feed."""
    if not ADAFRUIT_IO_USERNAME or not ADAFRUIT_IO_KEY:
        return None
    
    url = f"https://io.adafruit.com/api/v2/{ADAFRUIT_IO_USERNAME}/feeds/{feed_key}/data/last"
    try:
        response = requests.get(url, headers=get_headers(), timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.error(f"AIO Get Error ({feed_key}): {e}")
    return None

def aio_publish(feed_key, value):
    """Publish a value to a specific feed."""
    if not ADAFRUIT_IO_USERNAME or not ADAFRUIT_IO_KEY:
        return False
    
    url = f"https://io.adafruit.com/api/v2/{ADAFRUIT_IO_USERNAME}/feeds/{feed_key}/data"
    payload = {"value": value}
    
    try:
        response = requests.post(url, headers=get_headers(), json=payload, timeout=5)
        return response.status_code in [200, 201]
    except Exception as e:
        logger.error(f"AIO Publish Error ({feed_key}): {e}")
        return False

# --- FIX: Added limit parameter to function definition ---
def aio_get_history(feed_key, start_time=None, end_time=None, limit=1000):
    """Fetch historical data for charts."""
    if not ADAFRUIT_IO_USERNAME or not ADAFRUIT_IO_KEY:
        return []

    url = f"https://io.adafruit.com/api/v2/{ADAFRUIT_IO_USERNAME}/feeds/{feed_key}/data"
    # Use the passed limit variable here
    params = {'limit': limit}
    
    if start_time: params['start_time'] = start_time
    if end_time: params['end_time'] = end_time

    try:
        response = requests.get(url, headers=get_headers(), params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.error(f"AIO History Error ({feed_key}): {e}")
    return []

# --- Routes ---

@app.route('/')
def index():
    """Serve main dashboard"""
    return render_template('index.html')

@app.route('/about')
def about():
    """Serve about page"""
    return render_template('about.html')

@app.route('/api/status')
def api_status():
    """Get aggregated system status from AIO feeds"""
    try:
        mode_data = aio_get_last(FEEDS['mode'])
        stealth_data = aio_get_last(FEEDS['stealth'])
        servo_data = aio_get_last(FEEDS['servo'])
        temp_data = aio_get_last(FEEDS['temperature'])
        hum_data = aio_get_last(FEEDS['humidity'])

        mode = mode_data['value'] if mode_data else "disarmed"
        
        stealth = False
        if stealth_data:
            val = str(stealth_data['value']).lower()
            stealth = val in ['1', 'on', 'true', 'enabled']

        servo_pos = 0
        if servo_data:
            val = str(servo_data['value']).lower()
            if val in ['lock', 'locked', '1'] or (val.isdigit() and int(val) > 0):
                servo_pos = 90 
        
        temp = float(temp_data['value']) if temp_data else None
        hum = float(hum_data['value']) if hum_data else None

        return jsonify({
            "status": {
                "mode": mode,
                "stealth_mode": stealth,
                "servo_position": servo_pos
            },
            "temperature": {
                "temperature": temp,
                "humidity": hum
            }
        })
    except Exception as e:
        logger.error(f"Status API error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/arm', methods=['POST'])
def api_arm():
    """Arm the system via AIO"""
    if aio_publish(FEEDS['mode'], "armed"):
        return jsonify({"success": True, "mode": "armed"})
    return jsonify({"success": False, "message": "Failed to communicate with cloud"}), 500

@app.route('/api/disarm', methods=['POST'])
def api_disarm():
    """Disarm the system via AIO"""
    if aio_publish(FEEDS['mode'], "disarmed"):
        return jsonify({"success": True, "mode": "disarmed"})
    return jsonify({"success": False, "message": "Failed to communicate with cloud"}), 500

@app.route('/api/stealth', methods=['POST'])
def api_stealth():
    """Toggle stealth mode via AIO"""
    data = request.json
    enabled = data.get('enabled', False)
    value = "ON" if enabled else "OFF"
    
    if aio_publish(FEEDS['stealth'], value):
        return jsonify({"success": True, "stealth": enabled})
    return jsonify({"success": False, "error": "Failed to publish"}), 500

@app.route('/api/logs')
def api_logs():
    """Get event logs from AIO"""
    try:
        # This call was failing before because limit wasn't in definition
        logs_data = aio_get_history(FEEDS['logs'], limit=50)
        formatted_logs = []
        
        for log in logs_data:
            try:
                details = json.loads(log['value'])
                formatted_logs.append({
                    "timestamp": log['created_at'],
                    "type": details.get('type', 'INFO'),
                    "details": details.get('details', '')
                })
            except:
                formatted_logs.append({
                    "timestamp": log['created_at'],
                    "type": "EVENT",
                    "details": log['value']
                })
                
        return jsonify({"logs": formatted_logs})
    except Exception as e:
        logger.error(f"Logs API error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/images')
def api_images():
    """List images from AIO (Photos feed)"""
    try:
        images_data = aio_get_history(FEEDS['photos'], limit=20)
        formatted_images = []
        
        for img in images_data:
            try:
                val = json.loads(img['value'])
                formatted_images.append({
                    'filename': val.get('value', 'unknown.jpg'),
                    'timestamp': img['created_at'],
                    'size': 0 
                })
            except:
                continue
                
        return jsonify({"images": formatted_images})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/images/<path:filename>')
def api_serve_image(filename):
    return "Image storage require S3 or similar in cloud deployment", 404

@app.route('/api/test/actuator', methods=['POST'])
def api_test_actuator():
    """Test actuators via AIO"""
    data = request.json
    actuator = data.get('actuator')
    value = data.get('value')
    
    feed_map = {
        'led': FEEDS['led'],
        'buzzer': FEEDS['buzzer'],
        'servo': FEEDS['servo'],
        'camera': None 
    }
    
    if actuator not in feed_map:
        return jsonify({"error": "Unknown actuator"}), 400
        
    feed = feed_map[actuator]
    if not feed:
        return jsonify({"error": "Actuator not remotely controllable"}), 400

    payload = value
    if actuator == 'led': payload = "blink"
    if actuator == 'buzzer': payload = "beep"
    if actuator == 'servo' and not value: payload = "unlock" 

    if aio_publish(feed, payload):
        return jsonify({"success": True})
    
    return jsonify({"error": "Failed to publish command"}), 500

@app.route('/api/history/<sensor_type>')
def api_history(sensor_type):
    """Get history for charts"""
    if sensor_type not in ['temperature', 'humidity', 'motion']:
        return jsonify({"success": False, "error": "Invalid sensor"}), 400
        
    start_time = request.args.get('start')
    end_time = request.args.get('end')
    
    # This call relies on the default limit=1000
    data = aio_get_history(FEEDS.get(sensor_type), start_time, end_time)
    return jsonify({"success": True, "data": data})

@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    """Handle settings"""
    if request.method == 'POST':
        logger.warning("Settings update requested but cloud storage is not implemented.")
        return jsonify({"success": True})
    
    return jsonify({
        "success": True,
        "settings": {
            "pre_alarm_delay_seconds": 30,
            "alarm_duration_seconds": 180,
            "motion_timeout_seconds": 60,
            "photo_interval_seconds": 5
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)