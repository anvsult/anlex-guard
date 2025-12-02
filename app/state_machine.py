"""
Security System State Machine
Core logic for managing system states and transitions
"""
import time
import logging
import threading
import json
from enum import Enum
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import queue

from hardware.sensors import PIRSensor, DHTSensor, RFIDReader
from hardware.camera import Camera
from hardware.actuators import LED, Buzzer, Servo
from services.adafruit_service import AdafruitService
from services.email_service import EmailService
from services.storage_service import StorageService

logger = logging.getLogger(__name__)

class SystemMode(Enum):
    """System operating modes"""
    DISARMED = "disarmed"
    ARMED = "armed"
    PRE_ALARM = "pre_alarm"
    ALARM = "alarm"

class LEDPattern(Enum):
    """LED blinking patterns"""
    OFF = "off"
    SOLID = "solid"
    SLOW_BLINK = "slow_blink"  # 1s on, 1s off
    FAST_BLINK = "fast_blink"  # 0.1s on, 0.1s off

class SecurityStateMachine:
    """
    Main security system state machine
    Coordinates all hardware and services
    """
    
    def __init__(self, config):
        self.config = config
        self._mode = SystemMode.DISARMED
        self._stealth_mode = False
        self._led_pattern = LEDPattern.SLOW_BLINK
        
        # Thread control
        self._running = False
        self._lock = threading.RLock()
        self._threads: List[threading.Thread] = []
        
        # Timing state
        self._last_motion_time = 0
        self._pre_alarm_start = 0
        self._alarm_start = 0
        self._last_photo_time = 0
        self._last_sensor_read = 0
        
        # Event log (in-memory, limited size)
        self._event_log: List[Dict[str, Any]] = []
        self._max_log_size = 1000
        
        # Task queue for async operations
        self._task_queue = queue.Queue()
        
        # Initialize hardware
        logger.info("Initializing hardware...")
        self._init_hardware()
        
        # Initialize services
        logger.info("Initializing services...")
        self._init_services()
        
        logger.info("State machine initialization complete")
    
    def _init_hardware(self):
        """Initialize all hardware components"""
        try:
            pins = self.config.pins
            
            self.pir = PIRSensor(
                gpio_pin=pins['pir_bcm'],
                debounce_time=self.config.logic['pir_debounce_seconds']
            )
            
            self.dht = DHTSensor(board_pin=pins['dht_bcm'])
            
            self.rfid = RFIDReader()
            
            self.camera = Camera(
                device_index=self.config.camera['device_index'],
                width=self.config.camera['width'],
                height=self.config.camera['height'],
                storage_dir="web/static/images"
            )
            
            self.led = LED(gpio_pin=pins['led_bcm'])
            
            self.buzzer = Buzzer(gpio_pin=pins['buzzer_bcm'])
            
            self.servo = Servo(
                gpio_pin=pins['servo_bcm'],
                locked_angle=self.config.servo_angles['locked'],
                unlocked_angle=self.config.servo_angles['unlocked']
            )
            
            logger.info("Hardware initialization successful")
            
        except Exception as e:
            logger.critical(f"Hardware initialization failed: {e}", exc_info=True)
            raise
    
    def _init_services(self):
        """Initialize cloud services"""
        try:
            # Adafruit IO
            aio_config = self.config.adafruit_io
            self.adafruit = AdafruitService(
                username=aio_config.get('username', ''),
                key=aio_config.get('key', ''),
                feeds=aio_config.get('feeds', {}),
                control_callback=self._handle_adafruit_control
            )
            
            # Email Service (SMTP via Brevo)
            email_config = self.config.email_config
            self.email = EmailService(
                smtp_host=email_config.get('smtp_host'),
                smtp_port=email_config.get('smtp_port'),
                smtp_user=email_config.get('smtp_user'),
                smtp_pass=email_config.get('smtp_pass'),
                from_email=email_config.get('alert_from'),
                to_email=email_config.get('alert_to')
            )
            
            # Storage Service
            self.storage = StorageService(base_dir="web/static/images")
            
            logger.info("Services initialization successful")
            
        except Exception as e:
            logger.error(f"Service initialization failed: {e}", exc_info=True)
            # Services are non-critical, continue without them
    
    # ==================== STATE MANAGEMENT ====================
    
    @property
    def mode(self) -> SystemMode:
        """Get current system mode"""
        with self._lock:
            return self._mode
    
    @property
    def stealth_mode(self) -> bool:
        """Get stealth mode status"""
        with self._lock:
            return self._stealth_mode
    
    @stealth_mode.setter
    def stealth_mode(self, enabled: bool):
        """Set stealth mode"""
        with self._lock:
            self._stealth_mode = enabled
            logger.info(f"Stealth mode: {'ENABLED' if enabled else 'DISABLED'}")
            
            # Update LED pattern if armed
            if self._mode == SystemMode.ARMED:
                self._led_pattern = LEDPattern.OFF if enabled else LEDPattern.SOLID
    
    def arm_system(self, source: str = "Manual") -> bool:
        """
        Arm the security system
        
        Args:
            source: Who/what triggered the arming
        
        Returns:
            True if successful, False if already armed
        """
        with self._lock:
            if self._mode != SystemMode.DISARMED:
                logger.warning(f"Cannot arm: system is {self._mode.value}")
                return False
            
            logger.info(f"ARMING system (source: {source})")
            
            # Lock the box
            self.servo.lock()
            
            # Visual feedback: 3 quick blinks
            threading.Thread(target=self._arm_blink_sequence, daemon=True).start()
            
            # Update state
            self._mode = SystemMode.ARMED
            self._led_pattern = LEDPattern.OFF if self._stealth_mode else LEDPattern.SOLID
            
            # Log event
            self._log_event("ARM", f"Source: {source}")
            
            # Notify cloud
            # Notify cloud (use descriptive string so UI shows 'armed')
            self._task_queue.put(("publish", ("mode", "armed")))
            
            return True
    
    def _arm_blink_sequence(self):
        """3 fast blinks when arming"""
        for _ in range(3):
            self.led.on()
            time.sleep(0.15)
            self.led.off()
            time.sleep(0.15)
    
    def disarm_system(self, source: str = "Manual") -> bool:
        """
        Disarm the security system
        
        Args:
            source: Who/what triggered the disarming
        
        Returns:
            True if successful
        """
        with self._lock:
            prev_mode = self._mode
            
            logger.info(f"DISARMING system (was: {prev_mode.value}, source: {source})")
            
            # Stop any alarms
            self.buzzer.stop()
            
            # Unlock the box
            self.servo.unlock()
            
            # Update state
            self._mode = SystemMode.DISARMED
            self._led_pattern = LEDPattern.SLOW_BLINK
            
            # Reset timers
            self._last_motion_time = 0
            self._pre_alarm_start = 0
            self._alarm_start = 0
            
            # Log event
            self._log_event("DISARM", f"Source: {source}, Previous: {prev_mode.value}")
            
            # Notify cloud
            # Notify cloud (use descriptive string so UI shows 'disarmed')
            self._task_queue.put(("publish", ("mode", "disarmed")))
            self._task_queue.put(("publish", ("alarm", 0)))
            
            return True
    
    # ==================== ADAFRUIT CONTROL HANDLER ====================
    
    def _handle_adafruit_control(self, feed_name: str, value: str):
        """
        Handle control commands from Adafruit IO
        
        Args:
            feed_name: Name of the control feed
            value: Value received from Adafruit IO
        """
        try:
            # Convert value to appropriate type
            value = str(value).strip().lower()
            
            if feed_name == 'led_control':
                # LED control: on, off, blink, blink-fast
                if value in ['1', 'on', 'true']:
                    self.led.on()
                    logger.info("LED turned ON via Adafruit IO")
                elif value in ['0', 'off', 'false']:
                    self.led.off()
                    logger.info("LED turned OFF via Adafruit IO")
                elif value == 'blink':
                    threading.Thread(target=self.led.blink, args=(3, 0.5, 0.5), daemon=True).start()
                    logger.info("LED blinking (slow) via Adafruit IO")
                elif value == 'blink-fast':
                    threading.Thread(target=self.led.blink, args=(5, 0.1, 0.1), daemon=True).start()
                    logger.info("LED blinking (fast) via Adafruit IO")
            
            elif feed_name == 'buzzer_control':
                # Buzzer control: on, off, beep, beep-twice, siren
                if value in ['1', 'on', 'siren', 'true']:
                    self.buzzer.start_siren()
                    logger.info("Buzzer siren started via Adafruit IO")
                elif value in ['0', 'off', 'stop', 'false']:
                    self.buzzer.stop()
                    logger.info("Buzzer stopped via Adafruit IO")
                elif value == 'beep':
                    threading.Thread(target=self.buzzer.beep, args=(0.2,), daemon=True).start()
                    logger.info("Buzzer beep via Adafruit IO")
                elif value == 'beep-twice':
                    threading.Thread(target=self.buzzer.beep_twice, args=(0.1,), daemon=True).start()
                    logger.info("Buzzer beep-twice via Adafruit IO")
            
            elif feed_name == 'servo_control':
                # Servo control: lock, unlock, or angle (0-180)
                if value in ['lock', 'locked', '1']:
                    self.servo.lock()
                    logger.info("Servo locked via Adafruit IO")
                    self._log_event("SERVO_LOCK", "Remote control via Adafruit IO")
                elif value in ['unlock', 'unlocked', '0']:
                    self.servo.unlock()
                    logger.info("Servo unlocked via Adafruit IO")
                    self._log_event("SERVO_UNLOCK", "Remote control via Adafruit IO")
                else:
                    # Try to parse as angle
                    try:
                        angle = int(float(value))
                        if 0 <= angle <= 180:
                            self.servo.servo.angle = angle
                            time.sleep(0.5)
                            self.servo.servo.detach()
                            self.servo.current_angle = angle
                            logger.info(f"Servo set to {angle}° via Adafruit IO")
                            self._log_event("SERVO_ANGLE", f"Set to {angle}° via Adafruit IO")
                    except ValueError:
                        logger.warning(f"Invalid servo angle: {value}")
            
            elif feed_name == 'stealth_mode':
                # Stealth mode control: on/off
                if value in ['1', 'on', 'true', 'enabled']:
                    self.stealth_mode = True
                    logger.info("Stealth mode ENABLED via Adafruit IO")
                    self._log_event("STEALTH_MODE", "Enabled via Adafruit IO")
                elif value in ['0', 'off', 'false', 'disabled']:
                    self.stealth_mode = False
                    logger.info("Stealth mode DISABLED via Adafruit IO")
                    self._log_event("STEALTH_MODE", "Disabled via Adafruit IO")
        
        except Exception as e:
            logger.error(f"Error handling Adafruit control command: {e}", exc_info=True)
    
    # ==================== EVENT HANDLING ====================
    
    def handle_motion(self):
        """Handle motion detection event"""
        now = time.time()
        
        with self._lock:
            self._last_motion_time = now
            
            if self._mode == SystemMode.DISARMED:
                logger.debug("Motion detected (disarmed, ignoring)")
                return
            
            # Publish motion to cloud
            self._task_queue.put(("publish", ("motion", 1)))
            
            if self._mode == SystemMode.ARMED:
                # Transition to PRE_ALARM
                logger.warning("MOTION DETECTED! Entering PRE-ALARM state")
                self._mode = SystemMode.PRE_ALARM
                self._pre_alarm_start = now
                self._led_pattern = LEDPattern.SOLID
                
                # Take first photo immediately
                self._task_queue.put(("capture_photo", "Motion Trigger"))
                
                # Log event
                self._log_event("MOTION_DETECTED", "Entering pre-alarm state")
                
            elif self._mode == SystemMode.ALARM:
                # Already in alarm, update last motion time
                # Check if we should take another photo
                if now - self._last_photo_time >= self.config.logic['photo_interval_seconds']:
                    self._task_queue.put(("capture_photo", "Alarm Interval"))
    
    def handle_rfid(self, tag_id: int):
        """Handle RFID tag scan"""
        authorized = self.config.authorized_rfids
        
        if not authorized:
            logger.error("No authorized RFID tags configured!")
            return
        
        # Check authorization
        is_authorized = any(str(tag_id) == str(auth_id) for auth_id in authorized)
        
        if not is_authorized:
            logger.warning(f"UNAUTHORIZED RFID attempt: {tag_id}")
            self._log_event("RFID_UNAUTHORIZED", f"Tag ID: {tag_id}")
            return
        
        logger.info(f"Authorized RFID scan: {tag_id}")
        
        # Toggle arm/disarm
        if self.mode == SystemMode.DISARMED:
            self.arm_system(f"RFID:{tag_id}")
        else:
            self.disarm_system(f"RFID:{tag_id}")
    
    # ==================== BACKGROUND LOOPS ====================
    
    def _loop_main_logic(self):
        """Main state machine logic loop"""
        logger.info("Main logic loop started")
        
        while self._running:
            try:
                with self._lock:
                    now = time.time()
                    mode = self._mode
                    
                    # PRE-ALARM state logic
                    if mode == SystemMode.PRE_ALARM:
                        elapsed = now - self._pre_alarm_start
                        
                        # Warning beeps every 5 seconds (unless stealth)
                        if not self._stealth_mode:
                            if int(elapsed) % 5 == 0 and (elapsed - int(elapsed) < 0.1):
                                self._task_queue.put(("beep", 0.2))
                        
                        # Check if pre-alarm expired
                        if elapsed > self.config.logic['pre_alarm_delay_seconds']:
                            logger.warning("PRE-ALARM EXPIRED! Triggering ALARM")
                            self._mode = SystemMode.ALARM
                            self._alarm_start = now
                            self._led_pattern = LEDPattern.FAST_BLINK
                            
                            # Start continuous alarm
                            self.buzzer.start_siren()
                            
                            # Send email alert
                            self._task_queue.put(("send_email_alert", None))
                            
                            # Log event
                            self._log_event("ALARM_TRIGGERED", "Pre-alarm timeout expired")
                            
                            # Notify cloud
                            self._task_queue.put(("publish", ("alarm", 1)))
                    
                    # ALARM state logic
                    elif mode == SystemMode.ALARM:
                        alarm_duration = now - self._alarm_start
                        motion_timeout = now - self._last_motion_time
                        
                        # Check if alarm duration exceeded
                        if alarm_duration > self.config.logic['alarm_duration_seconds']:
                            logger.info("Alarm duration expired, returning to ARMED")
                            self._mode = SystemMode.ARMED
                            self.buzzer.stop()
                            self._led_pattern = LEDPattern.OFF if self._stealth_mode else LEDPattern.SOLID
                            self._log_event("ALARM_RESET", "Duration timeout")
                            self._task_queue.put(("publish", ("alarm", 0)))
                        
                        # Check if no motion for extended period
                        elif motion_timeout > self.config.logic['motion_timeout_seconds']:
                            logger.info("No motion detected, returning to ARMED")
                            self._mode = SystemMode.ARMED
                            self.buzzer.stop()
                            self._led_pattern = LEDPattern.OFF if self._stealth_mode else LEDPattern.SOLID
                            self._log_event("ALARM_RESET", "Motion timeout")
                            self._task_queue.put(("publish", ("alarm", 0)))
                
                time.sleep(0.1)  # 100ms tick
                
            except Exception as e:
                logger.error(f"Error in main logic loop: {e}", exc_info=True)
                time.sleep(1)
        
        logger.info("Main logic loop stopped")
    
    def _loop_led_control(self):
        """LED pattern control loop"""
        logger.info("LED control loop started")
        
        while self._running:
            try:
                pattern = self._led_pattern
                
                if pattern == LEDPattern.OFF:
                    self.led.off()
                    time.sleep(0.5)
                
                elif pattern == LEDPattern.SOLID:
                    self.led.on()
                    time.sleep(0.5)
                
                elif pattern == LEDPattern.SLOW_BLINK:
                    self.led.on()
                    time.sleep(1.0)
                    if not self._running: break
                    self.led.off()
                    time.sleep(1.0)
                
                elif pattern == LEDPattern.FAST_BLINK:
                    self.led.on()
                    time.sleep(0.1)
                    if not self._running: break
                    self.led.off()
                    time.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"Error in LED loop: {e}", exc_info=True)
                time.sleep(1)
        
        self.led.off()
        logger.info("LED control loop stopped")
    
    def _loop_motion_sensor(self):
        """PIR motion sensor polling loop"""
        logger.info("Motion sensor loop started")
        
        while self._running:
            try:
                if self.pir.motion_detected():
                    self.handle_motion()
                
                time.sleep(self.config.logic.get('read_interval_seconds', 0.5))
                
            except Exception as e:
                logger.error(f"Error in motion sensor loop: {e}", exc_info=True)
                time.sleep(1)
        
        logger.info("Motion sensor loop stopped")
    
    def _loop_rfid_reader(self):
        """RFID reader polling loop"""
        logger.info("RFID reader loop started")
        
        while self._running:
            try:
                tag_id = self.rfid.read()
                if tag_id:
                    self.handle_rfid(tag_id)
                    time.sleep(2)  # Debounce: prevent rapid re-reads
                else:
                    time.sleep(0.3)
                    
            except Exception as e:
                logger.error(f"Error in RFID loop: {e}", exc_info=True)
                time.sleep(1)
        
        logger.info("RFID reader loop stopped")
    
    def _loop_environmental_sensors(self):
        """Temperature/Humidity sensor reading loop"""
        logger.info("Environmental sensors loop started")
        
        while self._running:
            try:
                temp, humidity = self.dht.read()
                
                if temp is not None and humidity is not None:
                    logger.debug(f"Environment: {temp}°C, {humidity}%")
                    
                    # Publish to cloud
                    self._task_queue.put(("publish", ("temperature", temp)))
                    self._task_queue.put(("publish", ("humidity", humidity)))
                
                time.sleep(60)  # Read every minute
                
            except Exception as e:
                logger.error(f"Error in environmental sensors loop: {e}", exc_info=True)
                time.sleep(60)
        
        logger.info("Environmental sensors loop stopped")
    
    def _loop_task_processor(self):
        """Process async tasks from queue"""
        logger.info("Task processor loop started")
        
        while self._running:
            try:
                # Get task with timeout
                task = self._task_queue.get(timeout=1)
                task_type, task_data = task
                
                # Process task
                if task_type == "publish":
                    feed_key, value = task_data
                    self.adafruit.publish(feed_key, value)
                
                elif task_type == "capture_photo":
                    reason = task_data
                    self._capture_and_upload_photo(reason)
                
                elif task_type == "beep":
                    duration = task_data
                    self.buzzer.beep_twice(duration)
                
                elif task_type == "send_email_alert":
                    self._send_email_alert()
                
                self._task_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing task: {e}", exc_info=True)
        
        logger.info("Task processor loop stopped")
    
    # ==================== HELPER METHODS ====================
    
    def _capture_and_upload_photo(self, reason: str):
        """Capture photo and upload to Adafruit IO"""
        try:
            filename = self.camera.capture()
            self._last_photo_time = time.time()
            
            logger.info(f"Photo captured: {filename} (Reason: {reason})")
            self._log_event("PHOTO", f"{reason}: {filename}")
            
            # Upload to Adafruit IO (base64 encoded)
            self.adafruit.upload_photo(filename, self.camera.storage_dir / filename)
            
        except Exception as e:
            logger.error(f"Failed to capture/upload photo: {e}", exc_info=True)
    
    def _send_email_alert(self):
        """Send email alert for alarm"""
        try:
            subject = "🚨 AnLex Guard: ALARM TRIGGERED!"
            body = f"""
SECURITY ALERT - ALARM TRIGGERED

Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
Mode: {self._mode.value}
Stealth Mode: {'Enabled' if self._stealth_mode else 'Disabled'}

An intruder has been detected by your AnLex Guard security system.
Photos are being captured and saved.

Please check your dashboard immediately.

- AnLex Guard Security System
"""
            
            self.email.send_alert(subject, body)
            logger.info("Email alert sent successfully")
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}", exc_info=True)
    
    def _log_event(self, event_type: str, details: str = ""):
        """Log an event to the event log"""
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": event_type,
            "details": details,
            "mode": self._mode.value
        }
        
        with self._lock:
            self._event_log.append(event)
            
            # Trim log if too large
            if len(self._event_log) > self._max_log_size:
                self._event_log.pop(0)
        
        logger.info(f"EVENT: {event_type} - {details}")
        
        # Also publish event log trigger to Adafruit IO
        # Publish the full event JSON so the frontend can parse and display it
        try:
            event_json = json.dumps(event)
        except Exception:
            event_json = str(event)

        self._task_queue.put(("publish", ("event_log", event_json)))
    
    def get_event_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent event log entries"""
        with self._lock:
            return list(reversed(self._event_log[-limit:]))
    
    def get_status(self) -> Dict[str, Any]:
        """Get current system status"""
        with self._lock:
            temp, humidity = self.dht.read()
            
            return {
                "status": {
                    "mode": self._mode.value,
                    "stealth_mode": self._stealth_mode,
                    "servo_position": self.servo.current_angle
                },
                "temperature": {
                    "temperature": temp,
                    "humidity": humidity
                }
            }
    
    # ==================== LIFECYCLE ====================
    
    def start(self):
        """Start all background threads"""
        if self._running:
            logger.warning("State machine already running")
            return
        
        logger.info("Starting state machine...")
        self._running = True
        
        # Connect to Adafruit IO
        self.adafruit.connect()
        
        # Start background threads
        threads = [
            ("Main Logic", self._loop_main_logic),
            ("LED Control", self._loop_led_control),
            ("Motion Sensor", self._loop_motion_sensor),
            ("RFID Reader", self._loop_rfid_reader),
            ("Environmental", self._loop_environmental_sensors),
            ("Task Processor", self._loop_task_processor),
        ]
        
        for name, target in threads:
            thread = threading.Thread(target=target, daemon=True, name=name)
            thread.start()
            self._threads.append(thread)
            logger.info(f"Started thread: {name}")
        
        # Ensure system starts in disarmed state with unlocked servo
        self.servo.unlock()
        
        logger.info("State machine started successfully")
    
    def stop(self):
        """Stop all threads and cleanup"""
        if not self._running:
            return
        
        logger.info("Stopping state machine...")
        self._running = False
        
        # Stop all alarms
        self.buzzer.stop()
        self.led.off()
        
        # Wait for threads to finish
        for thread in self._threads:
            thread.join(timeout=2)
        
        # Cleanup hardware
        try:
            self.led.cleanup()
            self.buzzer.cleanup()
            self.servo.cleanup()
            logger.info("Hardware cleanup complete")
        except Exception as e:
            logger.error(f"Error during hardware cleanup: {e}")
        
        # Disconnect services
        self.adafruit.disconnect()
        
        logger.info("State machine stopped")