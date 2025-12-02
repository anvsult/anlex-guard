"""
Actuator Hardware Modules
LED, Buzzer, Servo Motor
"""
import logging
import time
import math
import threading
from gpiozero import LED as GPIOZeroLED, AngularServo, PWMOutputDevice

logger = logging.getLogger(__name__)

class LED:
    """LED Indicator"""
    
    def __init__(self, gpio_pin: int):
        """
        Initialize LED
        
        Args:
            gpio_pin: BCM GPIO pin number
        """
        self.gpio_pin = gpio_pin
        # underlying gpiozero LED instance
        self._gpio_led = GPIOZeroLED(gpio_pin)
        # when True, background loops should be suspended (blink will set this)
        self._suspend_background = False
        logger.info(f"LED initialized on GPIO {gpio_pin}")
    
    def on(self, force: bool = False):
        """Turn LED on

        Args:
            force: if True, apply regardless of background suspend (used by blink)
        """
        if self._suspend_background and not force:
            return
        self._gpio_led.on()
    
    def off(self, force: bool = False):
        """Turn LED off

        Args:
            force: if True, apply regardless of background suspend (used by blink)
        """
        if self._suspend_background and not force:
            return
        self._gpio_led.off()
    
    def blink(self, count: int = 3, on_time: float = 0.1, off_time: float = 0.1):
        """
        Blink LED
        
        Args:
            count: Number of blinks
            on_time: Time LED is on (seconds)
            off_time: Time LED is off (seconds)
        """
        # Suspend background control so the LED loop won't override our quick sequence
        prev_suspend = self._suspend_background
        self._suspend_background = True

        try:
            # Ensure LED starts OFF so quick blinks are visible
            self.off(force=True)
            time.sleep(0.05)

            for _ in range(count):
                self.on(force=True)
                time.sleep(on_time)
                self.off(force=True)
                time.sleep(off_time)

        finally:
            # Restore background control state
            self._suspend_background = prev_suspend
    def cleanup(self):
        """Cleanup GPIO resources"""
        self.off(force=True)
        try:
            self._gpio_led.close()
        except Exception:
            pass

class Buzzer:
    """Active Buzzer with PWM"""
    
    def __init__(self, gpio_pin: int, frequency: int = 2000):
        """
        Initialize buzzer
        
        Args:
            gpio_pin: BCM GPIO pin number
            frequency: Default frequency (Hz)
        """
        self.gpio_pin = gpio_pin
        self.default_frequency = frequency
        self.buzzer = PWMOutputDevice(gpio_pin, frequency=frequency)
        
        self._siren_running = False
        self._siren_thread = None
        
        logger.info(f"Buzzer initialized on GPIO {gpio_pin}")
    
    def beep(self, duration: float = 0.1):
        """
        Single beep
        
        Args:
            duration: Beep duration (seconds)
        """
        self.buzzer.frequency = self.default_frequency
        self.buzzer.value = 0.5  # 50% duty cycle
        time.sleep(duration)
        self.buzzer.off()
    
    def beep_twice(self, duration: float = 0.05):
        """
        Double beep for pre-alarm warnings
        
        Args:
            duration: Duration of each beep (seconds)
        """
        self.beep(duration)
        time.sleep(0.05)
        self.beep(duration)
    
    def start_siren(self):
        """Start continuous siren sound"""
        if not self._siren_running:
            self._siren_running = True
            self._siren_thread = threading.Thread(target=self._siren_loop, daemon=True)
            self._siren_thread.start()
            logger.info("Siren started")
    
    def stop(self):
        """Stop siren"""
        if self._siren_running:
            self._siren_running = False
            if self._siren_thread:
                self._siren_thread.join(timeout=1.0)
            self.buzzer.off()
            logger.info("Siren stopped")
    
    def _siren_loop(self):
        """Background siren loop with sine wave modulation"""
        try:
            while self._siren_running:
                for x in range(0, 361, 2):  # Step by 2 for performance
                    if not self._siren_running:
                        break
                    
                    sin_val = math.sin(x * (math.pi / 180))
                    frequency = 2000 + sin_val * 500
                    
                    self.buzzer.frequency = frequency
                    self.buzzer.value = 0.5
                    time.sleep(0.002)
                    
        except Exception as e:
            logger.error(f"Siren loop error: {e}")
        finally:
            self.buzzer.off()
    
    def cleanup(self):
        """Cleanup GPIO resources"""
        self.stop()
        self.buzzer.close()

class Servo:
    """Servo Motor for box locking mechanism"""
    
    def __init__(self, gpio_pin: int, locked_angle: int = 90, unlocked_angle: int = 0):
        """
        Initialize servo
        
        Args:
            gpio_pin: BCM GPIO pin number
            locked_angle: Angle for locked position (0-180)
            unlocked_angle: Angle for unlocked position (0-180)
        """
        self.gpio_pin = gpio_pin
        self.locked_angle = locked_angle
        self.unlocked_angle = unlocked_angle
        
        self.servo = AngularServo(
            gpio_pin,
            min_angle=0,
            max_angle=180,
            min_pulse_width=0.0005,
            max_pulse_width=0.0025
        )
        self.servo.detach()  # Start detached to prevent jitter
        
        self.current_angle = None
        logger.info(f"Servo initialized on GPIO {gpio_pin}")
    
    def lock(self):
        """Lock the box"""
        if self.current_angle == self.locked_angle:
            logger.debug(f"Servo already locked at {self.locked_angle}°")
            return
        
        logger.info(f"Locking servo to {self.locked_angle}°")
        self.servo.angle = self.locked_angle
        time.sleep(0.5)  # Wait for movement
        self.servo.detach()
        self.current_angle = self.locked_angle
    
    def unlock(self):
        """Unlock the box"""
        if self.current_angle == self.unlocked_angle:
            logger.debug(f"Servo already unlocked at {self.unlocked_angle}°")
            return
        
        logger.info(f"Unlocking servo to {self.unlocked_angle}°")
        self.servo.angle = self.unlocked_angle
        time.sleep(0.5)
        self.servo.detach()
        self.current_angle = self.unlocked_angle
    
    def cleanup(self):
        """Cleanup GPIO resources"""
        self.servo.detach()
        self.servo.close()