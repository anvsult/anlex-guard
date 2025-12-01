"""
Configuration Manager
Loads and validates system configuration from JSON and environment variables
"""
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class Config:
    """Central configuration manager"""
    
    def __init__(self, config_file: str = "config/config.json"):
        self.base_dir = Path(__file__).parent.parent
        self.config_file = self.base_dir / config_file
        
        # Load environment variables
        env_path = self.base_dir / '.env'
        if env_path.exists():
            load_dotenv(env_path)
            logger.info(f"Loaded environment from {env_path}")
        
        # Load JSON config
        self._config = self._load_json_config()
        
        # Override with environment variables
        self._apply_env_overrides()
        
        # Validate configuration
        self._validate()
    
    def _load_json_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            logger.info(f"Loaded configuration from {self.config_file}")
            return config
        except FileNotFoundError:
            logger.error(f"Config file not found: {self.config_file}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}")
            raise
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides"""
        # Adafruit IO
        if os.getenv('ADAFRUIT_IO_USERNAME'):
            self._config['adafruit_io']['username'] = os.getenv('ADAFRUIT_IO_USERNAME')
        if os.getenv('ADAFRUIT_IO_KEY'):
            self._config['adafruit_io']['key'] = os.getenv('ADAFRUIT_IO_KEY')
        
        # Brevo Email
        if os.getenv('BREVO_API_KEY'):
            self._config['email'] = self._config.get('email', {})
            self._config['email']['brevo_api_key'] = os.getenv('BREVO_API_KEY')
        if os.getenv('EMAIL_FROM'):
            self._config['email']['from_email'] = os.getenv('EMAIL_FROM')
        if os.getenv('EMAIL_TO'):
            self._config['email']['to_email'] = os.getenv('EMAIL_TO')
        
        # RFID Keys
        rfid_ids = os.getenv('AUTHORIZED_RFID_IDS', '')
        if rfid_ids:
            self._config['authorized_rfids'] = [
                int(x.strip()) for x in rfid_ids.split(',') if x.strip()
            ]
            logger.info(f"Loaded {len(self._config['authorized_rfids'])} authorized RFID keys")
    
    def _validate(self):
        """Validate required configuration"""
        required = ['pins', 'camera', 'logic', 'servo_angle']
        for key in required:
            if key not in self._config:
                raise ValueError(f"Missing required config section: {key}")
        
        if not self._config.get('authorized_rfids'):
            logger.warning("No authorized RFID keys configured!")
    
    def get(self, key: str, default=None):
        """Get configuration value"""
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set configuration value (runtime only, not persisted)"""
        self._config[key] = value
    
    def save_logic_config(self):
        """Save logic configuration back to JSON file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self._config, f, indent=2)
            logger.info("Configuration saved to file")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise
    
    @property
    def pins(self) -> Dict[str, Any]:
        return self._config['pins']
    
    @property
    def camera(self) -> Dict[str, Any]:
        return self._config['camera']
    
    @property
    def logic(self) -> Dict[str, Any]:
        return self._config['logic']
    
    @property
    def servo_angles(self) -> Dict[str, int]:
        return self._config['servo_angle']
    
    @property
    def adafruit_io(self) -> Dict[str, Any]:
        return self._config.get('adafruit_io', {})
    
    @property
    def email_config(self) -> Dict[str, Any]:
        return self._config.get('email', {})
    
    @property
    def authorized_rfids(self) -> List[int]:
        return self._config.get('authorized_rfids', [])
```

### `app/logging_config.py`
```python
"""
Centralized logging configuration
"""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

def setup_logging(log_dir: str = "data/logs", log_level: int = logging.INFO):
    """
    Configure application-wide logging
    
    Args:
        log_dir: Directory for log files
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Create log directory
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console Handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_format = logging.Formatter(
        '%(asctime)s [%(levelname)-8s] %(name)-20s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)
    
    # File Handler (rotating)
    file_handler = RotatingFileHandler(
        filename=Path(log_dir) / 'anlex_guard.log',
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=10,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_format = logging.Formatter(
        '%(asctime)s [%(levelname)-8s] [%(process)d-%(thread)d] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_format)
    root_logger.addHandler(file_handler)
    
    # Suppress noisy libraries
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)
    
    logging.info("Logging system initialized")