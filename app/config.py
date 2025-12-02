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
        
        # Brevo Email - REST API (deprecated)
        if os.getenv('BREVO_API_KEY'):
            self._config['email'] = self._config.get('email', {})
            self._config['email']['brevo_api_key'] = os.getenv('BREVO_API_KEY')
        if os.getenv('EMAIL_FROM'):
            self._config['email']['from_email'] = os.getenv('EMAIL_FROM')
        if os.getenv('EMAIL_TO'):
            self._config['email']['to_email'] = os.getenv('EMAIL_TO')
        
        # Brevo SMTP Configuration (preferred)
        if os.getenv('SMTP_HOST'):
            self._config['email'] = self._config.get('email', {})
            self._config['email']['smtp_host'] = os.getenv('SMTP_HOST')
        if os.getenv('SMTP_PORT'):
            self._config['email']['smtp_port'] = int(os.getenv('SMTP_PORT'))
        if os.getenv('SMTP_USER'):
            self._config['email']['smtp_user'] = os.getenv('SMTP_USER')
        if os.getenv('SMTP_PASS'):
            self._config['email']['smtp_pass'] = os.getenv('SMTP_PASS')
        if os.getenv('ALERT_FROM'):
            self._config['email']['alert_from'] = os.getenv('ALERT_FROM')
        if os.getenv('ALERT_TO'):
            self._config['email']['alert_to'] = os.getenv('ALERT_TO')
        
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