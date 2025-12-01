"""
API Routes for Dashboard (Raspberry Pi with Hardware)
Handles local hardware + Adafruit IO integration
"""
import logging
from flask import jsonify, request, render_template, send_from_directory, current_app
from functools import wraps

logger = logging.getLogger(__name__)

def get_system():
    """Get state machine instance"""
    return current_app.config['SYSTEM']

def get_config():
    """Get config instance"""
    return current_app.config['CONFIG']

def register_routes(app):
    """Register all API routes"""
    
    # ==================== WEB UI ====================
    
    @app.route('/')
    def index():
        """Serve main dashboard"""
        return render_template('index.html')
    
    @app.route('/about')
    def about():
        """Serve about page"""
        return render_template('about.html')
    
    # ==================== SYSTEM STATUS ====================
    
    @app.route('/api/status')
    def api_status():
        """Get current system status"""
        try:
            system = get_system()
            status = system.get_status()
            return jsonify(status)
        except Exception as e:
            logger.error(f"Status API error: {e}")
            return jsonify({"error": str(e)}), 500
    
    # ==================== SYSTEM CONTROL ====================
    
    @app.route('/api/arm', methods=['POST'])
    def api_arm():
        """Arm the security system"""
        try:
            system = get_system()
            success = system.arm_system(source="Dashboard")
            
            if success:
                system.adafruit.publish('mode', 'armed')
                return jsonify({"success": True, "mode": "armed"})
            else:
                return jsonify({"success": False, "message": "Already armed or in alarm"}), 400
        except Exception as e:
            logger.error(f"Arm API error: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/disarm', methods=['POST'])
    def api_disarm():
        """Disarm the security system"""
        try:
            system = get_system()
            success = system.disarm_system(source="Dashboard")
            
            system.adafruit.publish('mode', 'disarmed')
            return jsonify({"success": True, "mode": "disarmed"})
        except Exception as e:
            logger.error(f"Disarm API error: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/stealth', methods=['POST'])
    def api_stealth():
        """Toggle stealth mode"""
        try:
            data = request.json
            enabled = data.get('enabled', False)
            
            system = get_system()
            system.stealth_mode = enabled
            
            system.adafruit.publish('stealth_mode', '1' if enabled else '0')
            
            return jsonify({"success": True, "stealth": enabled})
        except Exception as e:
            logger.error(f"Stealth API error: {e}")
            return jsonify({"error": str(e)}), 500
    
    # ==================== EVENT LOGS ====================
    
    @app.route('/api/logs')
    def api_logs():
        """Get event logs"""
        try:
            limit = int(request.args.get('limit', 100))
            system = get_system()
            logs = system.get_event_log(limit=limit)
            
            return jsonify({"logs": logs})
        except Exception as e:
            logger.error(f"Logs API error: {e}")
            return jsonify({"error": str(e)}), 500
    
    # ==================== CAMERA & IMAGES ====================
    
    @app.route('/api/images')
    def api_images():
        """List captured images"""
        try:
            system = get_system()
            images = system.storage.list_images(limit=100)
            return jsonify({"images": images})
        except Exception as e:
            logger.error(f"Images API error: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/images/')
    def api_serve_image(filename):
        """Serve a specific image"""
        return send_from_directory('web/static/images', filename)
    
    # ==================== ACTUATOR CONTROL (via Adafruit IO) ====================
    
    @app.route('/api/control/led', methods=['POST'])
    def api_control_led():
        """Control LED via Adafruit IO"""
        try:
            data = request.json
            action = data.get('action', 'blink-fast')  # on, off, blink, blink-fast
            
            system = get_system()
            system.adafruit.publish('led_control', action)
            
            return jsonify({"success": True, "action": action})
        except Exception as e:
            logger.error(f"LED control error: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/control/buzzer', methods=['POST'])
    def api_control_buzzer():
        """Control buzzer via Adafruit IO"""
        try:
            data = request.json
            action = data.get('action', 'beep')  # on, off, beep, beep-twice, siren
            
            system = get_system()
            system.adafruit.publish('buzzer_control', action)
            
            return jsonify({"success": True, "action": action})
        except Exception as e:
            logger.error(f"Buzzer control error: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/control/servo', methods=['POST'])
    def api_control_servo():
        """Control servo via Adafruit IO"""
        try:
            data = request.json
            action = data.get('action')  # lock, unlock
            
            if action not in ['lock', 'unlock']:
                return jsonify({"error": "Invalid action. Use 'lock' or 'unlock'"}), 400
            
            system = get_system()
            system.adafruit.publish('servo_control', action)
            
            return jsonify({"success": True, "action": action})
        except Exception as e:
            logger.error(f"Servo control error: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/control/camera', methods=['POST'])
    def api_control_camera():
        """Capture photo (direct hardware control)"""
        try:
            system = get_system()
            filename = system.camera.capture()
            system._log_event("PHOTO", f"Manual capture: {filename}")
            return jsonify({"success": True, "filename": filename})
        except Exception as e:
            logger.error(f"Camera capture error: {e}")
            return jsonify({"error": str(e)}), 500
    
    # ==================== HISTORICAL DATA ====================
    
    @app.route('/api/history/temperature')
    def api_history_temperature():
        """Get temperature history from Adafruit IO"""
        try:
            start_time = request.args.get('start')
            end_time = request.args.get('end')
            
            system = get_system()
            data = system.adafruit.get_historical_data(
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
            
            system = get_system()
            data = system.adafruit.get_historical_data(
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
            
            system = get_system()
            data = system.adafruit.get_historical_data(
                'motion',
                start_time=start_time,
                end_time=end_time
            )
            
            return jsonify({"success": True, "data": data})
        except Exception as e:
            logger.error(f"Motion history error: {e}")
            return jsonify({"success": False, "error": str(e), "data": []})
    
    # ==================== SETTINGS ====================
    
    @app.route('/api/settings', methods=['GET'])
    def api_get_settings():
        """Get current settings"""
        try:
            config = get_config()
            return jsonify({
                "success": True,
                "settings": config.logic
            })
        except Exception as e:
            logger.error(f"Get settings error: {e}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/settings', methods=['POST'])
    def api_save_settings():
        """Save settings"""
        try:
            data = request.json
            config = get_config()
            
            # Update logic configuration
            if 'pre_alarm_delay_seconds' in data:
                config.logic['pre_alarm_delay_seconds'] = int(data['pre_alarm_delay_seconds'])
            if 'alarm_duration_seconds' in data:
                config.logic['alarm_duration_seconds'] = int(data['alarm_duration_seconds'])
            if 'motion_timeout_seconds' in data:
                config.logic['motion_timeout_seconds'] = int(data['motion_timeout_seconds'])
            if 'photo_interval_seconds' in data:
                config.logic['photo_interval_seconds'] = int(data['photo_interval_seconds'])
            
            # Save to file
            config.save_logic_config()
            
            logger.info("Settings saved successfully")
            return jsonify({"success": True})
            
        except Exception as e:
            logger.error(f"Save settings error: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500
    
    logger.info("API routes registered")