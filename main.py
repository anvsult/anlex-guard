"""
AnLex Guard - Home Security System
Main entry point
"""
import sys
import signal
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import Config
from app.logging_config import setup_logging
from app.state_machine import SecurityStateMachine
from api.app import create_app

# Global references
state_machine = None
flask_app = None

def signal_handler(sig, frame):
    """Handle shutdown signals gracefully"""
    logger = logging.getLogger(__name__)
    logger.info("Shutdown signal received")
    
    if state_machine:
        state_machine.stop()
    
    sys.exit(0)

def main():
    """Main application entry point"""
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("AnLex Guard Security System Starting...")
    logger.info("=" * 60)
    
    try:
        # Load configuration
        config = Config()
        logger.info(f"Configuration loaded: {config.config_file}")
        
        # Initialize state machine
        global state_machine
        state_machine = SecurityStateMachine(config)
        state_machine.start()
        logger.info("State machine initialized and started")
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Create and run Flask app
        global flask_app
        flask_app = create_app(config, state_machine)
        
        logger.info("Starting Flask web server on http://0.0.0.0:5000")
        flask_app.run(
            host='0.0.0.0',
            port=5000,
            debug=False,
            use_reloader=False  # Critical: prevents GPIO double-init
        )
        
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        return 1
    finally:
        if state_machine:
            state_machine.stop()
        logger.info("AnLex Guard shutdown complete")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())