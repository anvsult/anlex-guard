"""
Flask Application Factory
"""
import logging
from flask import Flask
from flask_cors import CORS

logger = logging.getLogger(__name__)

def create_app(config, state_machine):
    """
    Create and configure Flask application
    
    Args:
        config: Configuration object
        state_machine: SecurityStateMachine instance
    
    Returns:
        Configured Flask app
    """
    app = Flask(
        __name__,
        template_folder='../web/templates',
        static_folder='../web/static'
    )
    
    # CORS configuration
    CORS(app)
    
    # Store references
    app.config['SYSTEM'] = state_machine
    app.config['CONFIG'] = config
    
    # Register routes
    from api.routes import register_routes
    register_routes(app)
    
    logger.info("Flask application created")
    return app