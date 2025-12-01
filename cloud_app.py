"""
Cloud deployment entry point for Render.com
Runs Flask app without hardware dependencies
"""
import os
import logging
from flask import Flask
from flask_cors import CORS
from api.cloud_routes import register_cloud_routes, init_cloud_services

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app():
    """Create and configure Flask application for cloud deployment"""
    app = Flask(
        __name__,
        template_folder='web/templates',
        static_folder='web/static'
    )
    
    # CORS configuration
    CORS(app)
    
    # Initialize cloud services
    if not init_cloud_services():
        logger.error("Failed to initialize cloud services")
    
    # Register routes
    register_cloud_routes(app)
    
    logger.info("Cloud Flask application created successfully")
    return app

# Create app instance
app = create_app()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
