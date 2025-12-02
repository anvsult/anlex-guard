"""
Adafruit IO Service
MQTT publishing and photo upload
"""
import ssl
import json
import time
import logging
import base64
import paho.mqtt.client as mqtt
import requests
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

class AdafruitService:
    """Adafruit IO MQTT and REST API client"""
    
    def __init__(self, username: str, key: str, feeds: Dict[str, str], control_callback=None):
        """
        Initialize Adafruit IO service
        
        Args:
            username: Adafruit IO username
            key: Adafruit IO key
            feeds: Dictionary mapping feed names to feed keys
            control_callback: Callback function for control commands (feed_name, value)
        """
        self.username = username
        self.key = key
        self.feeds = feeds
        self.host = "io.adafruit.com"
        self.port = 8883
        self.control_callback = control_callback
        
        self._connected = False
        
        # MQTT Client
        client_id = f"anlex-guard-{int(time.time())}"
        self.client = mqtt.Client(
            client_id=client_id,
            clean_session=True,
            protocol=mqtt.MQTTv311
        )
        
        self.client.username_pw_set(username, key)
        self.client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
        self.client.tls_insecure_set(False)
        
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
        # Control feeds to subscribe to
        self._control_feeds = ['led_control', 'buzzer_control', 'servo_control', 'stealth_mode']
        
        logger.info("Adafruit IO service initialized")
    
    def _on_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            self._connected = True
            logger.info("Adafruit IO connected")
            
            # Subscribe to control feeds
            for feed_name in self._control_feeds:
                feed_key = self.feeds.get(feed_name)
                if feed_key:
                    topic = f"{self.username}/feeds/{feed_key}"
                    self.client.subscribe(topic, qos=1)
                    logger.info(f"Subscribed to control feed: {feed_name}")
        else:
            logger.error(f"Adafruit IO connection failed: rc={rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback"""
        self._connected = False
        logger.warning(f"Adafruit IO disconnected: rc={rc}")
    
    def _on_message(self, client, userdata, msg):
        """MQTT message received callback"""
        try:
            # Parse topic to get feed key
            topic_parts = msg.topic.split('/')
            if len(topic_parts) >= 3:
                feed_key = topic_parts[2]
                
                # Find feed name from feed key
                feed_name = None
                for name, key in self.feeds.items():
                    if key == feed_key:
                        feed_name = name
                        break
                
                if feed_name and feed_name in self._control_feeds:
                    # Parse payload
                    payload = msg.payload.decode('utf-8')
                    
                    # Try to parse JSON, fallback to plain string
                    try:
                        data = json.loads(payload)
                        value = data.get('value', payload)
                    except json.JSONDecodeError:
                        value = payload
                    
                    logger.info(f"Control command received: {feed_name} = {value}")
                    
                    # Call control callback
                    if self.control_callback:
                        self.control_callback(feed_name, value)
                    
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}", exc_info=True)
    
    def connect(self):
        """Connect to Adafruit IO MQTT broker"""
        try:
            self.client.connect_async(self.host, self.port, keepalive=60)
            self.client.loop_start()
            logger.info("Adafruit IO connection initiated")
        except Exception as e:
            logger.error(f"Failed to connect to Adafruit IO: {e}")
    
    def disconnect(self):
        """Disconnect from Adafruit IO"""
        try:
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("Adafruit IO disconnected")
        except Exception:
            pass
    
    def publish(self, feed_name: str, value: Any):
        """
        Publish data to Adafruit IO feed
        
        Args:
            feed_name: Feed name (from feeds config)
            value: Value to publish
        """
        # Resolve feed key
        feed_key = self.feeds.get(feed_name)
        if not feed_key:
            logger.warning(f"Unknown feed: {feed_name}")
            return False

        topic = f"{self.username}/feeds/{feed_key}"
        payload = json.dumps({"value": value})

        success = False

        # Try MQTT publish if connected
        if self._connected:
            try:
                result = self.client.publish(topic, payload=payload, qos=1)
                rc = getattr(result, 'rc', None)
                if rc == mqtt.MQTT_ERR_SUCCESS:
                    logger.debug(f"Published via MQTT to {feed_name}: {value}")
                    success = True
                else:
                    logger.warning(f"MQTT publish returned rc={rc}")
            except Exception as e:
                logger.error(f"MQTT publish error: {e}", exc_info=True)

        # Fallback to REST API if MQTT unavailable or failed
        if not success:
            try:
                url = f"https://io.adafruit.com/api/v2/{self.username}/feeds/{feed_key}/data"
                headers = {'X-AIO-Key': self.key, 'Content-Type': 'application/json'}
                response = requests.post(url, headers=headers, json={"value": value}, timeout=5)
                if response.status_code in (200, 201):
                    logger.debug(f"Published via REST to {feed_name}: {value}")
                    success = True
                else:
                    logger.warning(f"REST publish failed: status={response.status_code} body={response.text}")
            except Exception as e:
                logger.error(f"REST publish error: {e}", exc_info=True)

        return success
    
    def upload_photo(self, filename: str, filepath: Path):
        """
        Upload photo to Adafruit IO (base64 encoded to a feed)
        
        Note: Adafruit IO has size limits. For production, use dedicated image storage.
        
        Args:
            filename: Name of the file
            filepath: Path to the image file
        """
        try:
            # Read and encode image
            with open(filepath, 'rb') as f:
                image_data = f.read()
            
            # Check size (Adafruit IO has ~100KB limit per value)
            if len(image_data) > 100000:
                logger.warning(f"Image too large for Adafruit IO: {len(image_data)} bytes")
                return
            
            b64_data = base64.b64encode(image_data).decode('utf-8')
            
            # Publish to a dedicated photo feed
            photo_feed = self.feeds.get('photos', 'photos')
            topic = f"{self.username}/feeds/{photo_feed}"
            
            payload = json.dumps({
                "value": filename,
                "metadata": {"image": b64_data}
            })
            
            self.client.publish(topic, payload=payload, qos=1)
            logger.info(f"Photo uploaded to Adafruit IO: {filename}")
            
        except Exception as e:
            logger.error(f"Failed to upload photo: {e}")
    
    def get_historical_data(self, feed_name: str, start_time: str = None, 
                           end_time: str = None, limit: int = 1000) -> list:
        """
        Fetch historical data from Adafruit IO REST API
        
        Args:
            feed_name: Feed name
            start_time: ISO format start time
            end_time: ISO format end time
            limit: Max number of data points
        
        Returns:
            List of data points
        """
        feed_key = self.feeds.get(feed_name)
        if not feed_key:
            logger.warning(f"Unknown feed: {feed_name}")
            return []
        
        try:
            url = f"https://io.adafruit.com/api/v2/{self.username}/feeds/{feed_key}/data"
            
            params = {'limit': min(limit, 1000)}
            if start_time:
                params['start_time'] = start_time
            if end_time:
                params['end_time'] = end_time
            
            headers = {'X-AIO-Key': self.key}
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Retrieved {len(data)} data points from {feed_name}")
                return data
            else:
                logger.error(f"Adafruit IO API error: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Failed to fetch data from Adafruit IO: {e}")
            return []