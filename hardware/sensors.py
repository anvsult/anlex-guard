"""
Sensor Hardware Modules
PIR Motion Sensor, DHT Temperature/Humidity, RFID Reader
"""
import logging
import time
import board
import adafruit_dht
import RPi.GPIO as GPIO
from gpiozero import MotionSensor
from mfrc522 import SimpleMFRC522

logger = logging.getLogger(__name__)

class PIRSensor:
    """PIR Motion Sensor"""
    
    def __init__(self, gpio_pin: int, debounce_time: float = 1.0):
        """
        Initialize PIR sensor
        
        Args:
            gpio_pin: BCM GPIO pin number
            debounce_time: Minimum time between motion detections (seconds)
        """
        self.gpio_pin = gpio_pin
        self.debounce_time = debounce_time
        self.sensor = MotionSensor(gpio_pin, queue_len=1, sample_rate=100, threshold=0.5)
        self._last_detection = 0
        logger.info(f"PIR sensor initialized on GPIO {gpio_pin}")
    
    def motion_detected(self) -> bool:
        """
        Check if motion is detected with debouncing
        
        Returns:
            True if motion detected, False otherwise
        """
        if self.sensor.motion_detected:
            now = time.time()
            if now - self._last_detection >= self.debounce_time:
                self._last_detection = now
                return True
        return False

class DHTSensor:
    """DHT11/DHT22 Temperature and Humidity Sensor"""
    
    def __init__(self, board_pin: str = "D4"):
        """
        Initialize DHT sensor
        
        Args:
            board_pin: Board pin designation (e.g., "D4" for GPIO4)
        """
        self.board_pin = board_pin
        self._sensor = None
        logger.info(f"DHT sensor initialized on {board_pin}")
    
    def read(self) -> tuple:
        """
        Read temperature and humidity
        
        Returns:
            Tuple of (temperature_celsius, humidity_percent) or (None, None) on error
        """
        try:
            # Lazy initialization (DHT sensors can be finicky)
            if self._sensor is None:
                pin_obj = getattr(board, self.board_pin)
                self._sensor = adafruit_dht.DHT11(pin_obj)
            
            temperature = self._sensor.temperature
            humidity = self._sensor.humidity
            
            if temperature is None or humidity is None:
                return None, None
            
            return float(temperature), float(humidity)
            
        except RuntimeError as e:
            # DHT sensors commonly throw RuntimeError for checksum/timeout
            logger.debug(f"DHT read error (normal): {e}")
            return None, None
            
        except Exception as e:
            logger.error(f"DHT critical error: {e}", exc_info=True)
            # Reset sensor on critical error
            if self._sensor:
                self._sensor.exit()
                self._sensor = None
            return None, None

class RFIDReader:
    """MFRC522 RFID Reader"""
    
    def __init__(self):
        """Initialize RFID reader"""
        GPIO.setwarnings(False)
        self.reader = SimpleMFRC522()
        logger.info("RFID reader initialized")
    
    def read(self) -> int:
        """
        Read RFID tag ID (blocking)
        
        Returns:
            Tag ID as integer, or None if read failed
        """
        try:
            tag_id, _ = self.reader.read_no_block()
            if tag_id:
                logger.info(f"RFID tag read: {tag_id}")
                return tag_id
            return None
        except Exception as e:
            logger.error(f"RFID read error: {e}")
            return None
