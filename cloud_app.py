"""
Cloud deployment entry point for Render.com
Runs Flask app without hardware dependencies
All actuator control happens through Adafruit IO MQTT feeds
"""
import os
import logging
import signal
import sys
from flask import Flask
from flask_cors import CORS
from api.cloud_routes import register_cloud_routes, init_cloud_services, shutdown_cloud_services

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def signal_handler(sig, frame):
    """Handle shutdown signals gracefully"""
    logger.info("Shutdown signal received, cleaning up cloud services...")
    shutdown_cloud_services()
    sys.exit(0)

def create_app():
    """Create and configure Flask application for cloud deployment"""
    app = Flask(
        __name__,
        template_folder='web/templates',
        static_folder='web/static'
    )
    
    # CORS configuration
    CORS(app)
    
    # Initialize cloud services (Adafruit IO MQTT connection)
    if not init_cloud_services():
        logger.error("Failed to initialize cloud services")
    else:
        logger.info("Cloud services initialized - All actuator control via Adafruit IO")
    
    # Register routes
    register_cloud_routes(app)
    
    logger.info("Cloud Flask application created successfully")
    return app

# Create app instance
app = create_app()

# Setup signal handlers for graceful shutdown
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    logger.info(f"Starting cloud server on port {port}")
    logger.info("All actuator controls will be sent to Adafruit IO feeds")
    app.run(host='0.0.0.0', port=port, debug=False)
