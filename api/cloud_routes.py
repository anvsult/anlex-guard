"""
Cloud-based API Routes - Works without hardware
All actuator control happens via Adafruit IO MQTT feeds
For deployment on Render.com or similar platforms
"""
import logging
import os
from flask import jsonify, request, render_template
from services.adafruit_service import AdafruitService

logger = logging.getLogger(__name__)

# Global Adafruit service instance
adafruit = None

def init_cloud_services():
    """Initialize Adafruit IO service for cloud deployment"""
    global adafruit
    
    username = os.getenv('ADAFRUIT_IO_USERNAME')
    key = os.getenv('ADAFRUIT_IO_KEY')
    
    if not username or not key:
        logger.error("Adafruit IO credentials not found in environment variables")
        logger.error("Please set ADAFRUIT_IO_USERNAME and ADAFRUIT_IO_KEY environment variables")
        return False
    
    feeds = {
        "motion": os.getenv('FEED_MOTION', 'sensor.motion'),
        "temperature": os.getenv('FEED_TEMPERATURE', 'sensor.temperature'),
        "humidity": os.getenv('FEED_HUMIDITY', 'sensor.humidity'),
        "mode": os.getenv('FEED_MODE', 'mode'),
        "alarm": os.getenv('FEED_ALARM', 'alarm'),
        "event_log": os.getenv('FEED_EVENTS', 'events'),
        "led_control": os.getenv('FEED_LED', 'actuator.led'),
        "buzzer_control": os.getenv('FEED_BUZZER', 'actuator.buzzer'),
        "servo_control": os.getenv('FEED_SERVO', 'actuator.servo'),
        "stealth_mode": os.getenv('FEED_STEALTH', 'control.stealth'),
    }
    
    logger.info(f"Initializing Adafruit IO connection for user: {username}")
    logger.info(f"Feed configuration: {feeds}")
    
    # Initialize Adafruit service (no control callback needed for cloud-only deployment)
    adafruit = AdafruitService(username, key, feeds, control_callback=None)
    
    # Connect to Adafruit IO MQTT broker
    adafruit.connect()
    
    # Give connection a moment to establish (async connection)
    import time
    time.sleep(2)
    
    logger.info("Cloud services initialized successfully")
    logger.info(f"Connected to Adafruit IO as {username}")
    logger.info(f"MQTT connection state: {'Connected' if adafruit._connected else 'Connecting...'}")
    logger.info("All actuator commands will be published to Adafruit IO feeds")
    return True

def shutdown_cloud_services():
    """Shutdown cloud services gracefully"""
    global adafruit
    if adafruit:
        logger.info("Disconnecting from Adafruit IO...")
        adafruit.disconnect()
        logger.info("Cloud services shutdown complete")

def register_cloud_routes(app):
    """Register cloud-only API routes"""
    
    # ==================== WEB UI ====================
    
    @app.route('/')
    def index():
        """Serve main dashboard"""
        return render_template('index.html')
    
    @app.route('/about')
    def about():
        """Serve about page"""
        return render_template('about.html')
    
    # ==================== SYSTEM STATUS (from Adafruit IO) ====================
    
    @app.route('/api/status')
    def api_status():
        """Get current system status from Adafruit IO"""
        try:
            # Get latest values from Adafruit IO
            temp_data = adafruit.get_historical_data('temperature', limit=1)
            hum_data = adafruit.get_historical_data('humidity', limit=1)
            motion_data = adafruit.get_historical_data('motion', limit=1)
            mode_data = adafruit.get_historical_data('mode', limit=1)
            stealth_data = adafruit.get_historical_data('stealth_mode', limit=1)
            
            status = {
                "status": {
                    "mode": mode_data[0]['value'] if mode_data else "disarmed",
                    "stealth_mode": stealth_data[0]['value'] == '1' if stealth_data else False,
                },
                "temperature": {
                    "temperature": float(temp_data[0]['value']) if temp_data else None,
                    "humidity": float(hum_data[0]['value']) if hum_data else None,
                    "last_update": temp_data[0]['created_at'] if temp_data else None
                },
                "motion": {
                    "detected": int(motion_data[0]['value']) > 0 if motion_data else False,
                    "last_update": motion_data[0]['created_at'] if motion_data else None
                }
            }
            
            return jsonify(status)
        except Exception as e:
            logger.error(f"Status API error: {e}")
            return jsonify({"error": str(e)}), 500
    
    # ==================== SYSTEM CONTROL (publish to Adafruit IO) ====================
    
    @app.route('/api/arm', methods=['POST'])
    def api_arm():
        """Arm the security system via Adafruit IO"""
        try:
            if not adafruit:
                return jsonify({"error": "Adafruit IO not initialized"}), 503
            
            # Publish to Adafruit IO - Raspberry Pi will receive and arm the system
            adafruit.publish('mode', 'armed')
            logger.info("System arm command published to Adafruit IO")
            
            return jsonify({
                "success": True, 
                "mode": "armed",
                "message": "Arm command sent to Adafruit IO feed 'mode'"
            })
        except Exception as e:
            logger.error(f"Arm API error: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/disarm', methods=['POST'])
    def api_disarm():
        """Disarm the security system via Adafruit IO"""
        try:
            if not adafruit:
                return jsonify({"error": "Adafruit IO not initialized"}), 503
            
            # Publish to Adafruit IO - Raspberry Pi will receive and disarm the system
            adafruit.publish('mode', 'disarmed')
            logger.info("System disarm command published to Adafruit IO")
            
            return jsonify({
                "success": True, 
                "mode": "disarmed",
                "message": "Disarm command sent to Adafruit IO feed 'mode'"
            })
        except Exception as e:
            logger.error(f"Disarm API error: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/stealth', methods=['POST'])
    def api_stealth():
        """Toggle stealth mode via Adafruit IO"""
        try:
            if not adafruit:
                return jsonify({"error": "Adafruit IO not initialized"}), 503
            
            data = request.json or {}
            enabled = data.get('enabled', False)
            
            # Publish to Adafruit IO - Raspberry Pi will receive and set stealth mode
            adafruit.publish('stealth_mode', '1' if enabled else '0')
            logger.info(f"Stealth mode {'enabled' if enabled else 'disabled'} command published to Adafruit IO")
            
            return jsonify({
                "success": True, 
                "stealth": enabled,
                "message": f"Stealth mode {'enabled' if enabled else 'disabled'} command sent to Adafruit IO"
            })
        except Exception as e:
            logger.error(f"Stealth API error: {e}")
            return jsonify({"error": str(e)}), 500
    
    # ==================== ACTUATOR CONTROL (via Adafruit IO) ====================
    
    @app.route('/api/control/led', methods=['POST'])
    def api_control_led():
        """Control LED via Adafruit IO feed"""
        try:
            if not adafruit:
                return jsonify({"error": "Adafruit IO not initialized"}), 503
            
            data = request.json or {}
            action = data.get('action', 'blink-fast')
            
            # Valid actions: on, off, blink, blink-fast
            valid_actions = ['on', 'off', 'blink', 'blink-fast', '1', '0']
            if action not in valid_actions:
                return jsonify({"error": f"Invalid action. Valid: {valid_actions}"}), 400
            
            # Publish to Adafruit IO - Raspberry Pi will receive and execute
            adafruit.publish('led_control', action)
            logger.info(f"LED control command published to Adafruit IO: {action}")
            
            return jsonify({
                "success": True, 
                "action": action,
                "message": "Command sent to Adafruit IO feed 'led_control'"
            })
        except Exception as e:
            logger.error(f"LED control error: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/control/buzzer', methods=['POST'])
    def api_control_buzzer():
        """Control buzzer via Adafruit IO feed"""
        try:
            if not adafruit:
                logger.error("Buzzer control failed: Adafruit IO not initialized")
                return jsonify({"error": "Adafruit IO not initialized"}), 503
            
            data = request.json or {}
            action = data.get('action', 'beep')
            
            # Valid actions: on, off, beep, beep-twice, siren
            valid_actions = ['on', 'off', 'beep', 'beep-twice', 'siren', 'stop', '1', '0']
            if action not in valid_actions:
                logger.warning(f"Invalid buzzer action attempted: {action}")
                return jsonify({"error": f"Invalid action. Valid: {valid_actions}"}), 400
            
            # Check MQTT connection status
            connection_status = "Connected" if adafruit._connected else "Disconnected"
            logger.info(f"Buzzer control request - Action: {action}, MQTT Status: {connection_status}")
            
            # Publish to Adafruit IO - Raspberry Pi will receive and execute
            feed_key = adafruit.feeds.get('buzzer_control')
            logger.info(f"Publishing to feed: buzzer_control (key: {feed_key})")
            adafruit.publish('buzzer_control', action)
            logger.info(f"Buzzer control command published to Adafruit IO: {action}")
            
            return jsonify({
                "success": True, 
                "action": action,
                "message": f"Command sent to Adafruit IO feed 'buzzer_control' (MQTT: {connection_status})"
            })
        except Exception as e:
            logger.error(f"Buzzer control error: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

        except Exception as e:
            logger.error(f"Buzzer control error: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/control/servo', methods=['POST'])
    def api_control_servo():
        """Control servo via Adafruit IO feed"""
        try:
            if not adafruit:
                return jsonify({"error": "Adafruit IO not initialized"}), 503
            
            data = request.json or {}
            action = data.get('action')
            
            # Valid actions: lock, unlock
            if action not in ['lock', 'unlock']:
                return jsonify({"error": "Invalid action. Use 'lock' or 'unlock'"}), 400
            
            # Publish to Adafruit IO - Raspberry Pi will receive and execute
            adafruit.publish('servo_control', action)
            logger.info(f"Servo control command published to Adafruit IO: {action}")
            
            return jsonify({
                "success": True, 
                "action": action,
                "message": "Command sent to Adafruit IO feed 'servo_control'"
            })
        except Exception as e:
            logger.error(f"Servo control error: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/control/camera', methods=['POST'])
    def api_control_camera():
        """Request camera capture via Adafruit IO (not available in cloud-only mode)"""
        try:
            # Note: Camera capture is handled by the Raspberry Pi hardware
            # This endpoint is here for API compatibility but doesn't do anything in cloud mode
            logger.warning("Camera capture requested in cloud-only mode - not available")
            return jsonify({
                "success": False, 
                "message": "Camera control not available in cloud-only deployment"
            }), 501
        except Exception as e:
            logger.error(f"Camera control error: {e}")
            return jsonify({"error": str(e)}), 500
    
    # ==================== HISTORICAL DATA (from Adafruit IO) ====================
    
    @app.route('/api/history/temperature')
    def api_history_temperature():
        """Get temperature history from Adafruit IO"""
        try:
            start_time = request.args.get('start')
            end_time = request.args.get('end')
            
            data = adafruit.get_historical_data(
                'temperature',
                start_time=start_time,
                end_time=end_time
            )
            
            return jsonify({"success": True, "data": data})
        except Exception as e:
            logger.error(f"Temperature history error: {e}")
            return jsonify({"success": False, "error": str(e), "data": []})
    
    @app.route('/api/history/humidity')
    def api_history_humidity():
        """Get humidity history from Adafruit IO"""
        try:
            start_time = request.args.get('start')
            end_time = request.args.get('end')
            
            data = adafruit.get_historical_data(
                'humidity',
                start_time=start_time,
                end_time=end_time
            )
            
            return jsonify({"success": True, "data": data})
        except Exception as e:
            logger.error(f"Humidity history error: {e}")
            return jsonify({"success": False, "error": str(e), "data": []})
    
    @app.route('/api/history/motion')
    def api_history_motion():
        """Get motion detection history from Adafruit IO"""
        try:
            start_time = request.args.get('start')
            end_time = request.args.get('end')
            
            data = adafruit.get_historical_data(
                'motion',
                start_time=start_time,
                end_time=end_time
            )
            
            return jsonify({"success": True, "data": data})
        except Exception as e:
            logger.error(f"Motion history error: {e}")
            return jsonify({"success": False, "error": str(e), "data": []})
    
    # ==================== EVENT LOGS (from Adafruit IO) ====================
    
    @app.route('/api/logs')
    def api_logs():
        """Get event logs from Adafruit IO"""
        try:
            limit = int(request.args.get('limit', 50))
            
            # Get recent event log entries from Adafruit IO
            data = adafruit.get_historical_data('event_log', limit=limit)
            
            # Transform to log format
            logs = []
            for item in data:
                logs.append({
                    "timestamp": item['created_at'],
                    "type": "EVENT",
                    "details": item.get('value', '')
                })
            
            return jsonify({"logs": logs})
        except Exception as e:
            logger.error(f"Logs API error: {e}")
            return jsonify({"error": str(e), "logs": []})
    
    # ==================== SETTINGS ====================
    
    @app.route('/api/settings', methods=['GET'])
    def api_get_settings():
        """Get current settings (returns defaults for cloud deployment)"""
        try:
            # For cloud deployment, return default settings
            # Settings are managed on the Raspberry Pi side
            settings = {
                "pre_alarm_delay_seconds": int(os.getenv('PRE_ALARM_DELAY', 30)),
                "alarm_duration_seconds": int(os.getenv('ALARM_DURATION', 180)),
                "motion_timeout_seconds": int(os.getenv('MOTION_TIMEOUT', 60)),
                "photo_interval_seconds": int(os.getenv('PHOTO_INTERVAL', 5))
            }
            return jsonify({
                "success": True,
                "settings": settings,
                "note": "Settings are managed on the Raspberry Pi. Changes here are for display only."
            })
        except Exception as e:
            logger.error(f"Get settings error: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/settings', methods=['POST'])
    def api_save_settings():
        """Save settings (not supported in cloud-only mode)"""
        try:
            # Settings cannot be saved in cloud-only mode
            # They must be configured on the Raspberry Pi
            logger.warning("Settings save attempted in cloud-only mode")
            return jsonify({
                "success": False,
                "message": "Settings cannot be saved in cloud-only mode. Configure settings on the Raspberry Pi.",
                "note": "Settings are stored in config/config.json on the Raspberry Pi."
            }), 501
        except Exception as e:
            logger.error(f"Save settings error: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500
    
    # ==================== HEALTH CHECK ====================
    
    @app.route('/api/health')
    def api_health():
        """Health check endpoint"""
        mqtt_connected = adafruit._connected if adafruit else False
        return jsonify({
            "status": "healthy",
            "service": "AnLex Guard Cloud API",
            "adafruit_initialized": adafruit is not None,
            "mqtt_connected": mqtt_connected,
            "feeds_configured": len(adafruit.feeds) if adafruit else 0
        })
    
    logger.info("Cloud API routes registered")
