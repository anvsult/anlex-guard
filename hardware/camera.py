import logging
import cv2
import threading
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class Camera:
    """USB Camera for capturing images"""
    
    def __init__(self, device_index: int = 0, width: int = 1280, height: int = 720, 
                 storage_dir: str = "data/images"):
        """
        Initialize camera
        
        Args:
            device_index: Camera device index (0 for /dev/video0)
            width: Image width
            height: Image height
            storage_dir: Directory to save captured images
        """
        self.device_index = device_index
        self.width = width
        self.height = height
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self._lock = threading.Lock()  # Camera is not thread-safe
        
        logger.info(f"Camera initialized: device {device_index}, {width}x{height}")
    
    def capture(self) -> str:
        """
        Capture a single image
        
        Returns:
            Filename of captured image
        
        Raises:
            RuntimeError: If capture fails
        """
        with self._lock:
            cap = None
            try:
                cap = cv2.VideoCapture(self.device_index)
                
                if not cap.isOpened():
                    raise RuntimeError("Camera not available")
                
                # Set resolution
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                
                # Let auto-exposure settle by reading a few frames
                for _ in range(5):
                    cap.read()
                
                # Capture frame
                success, frame = cap.read()
                if not success:
                    raise RuntimeError("Failed to read frame from camera")
                
                # Generate filename
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                filename = f"capture_{timestamp}.jpg"
                filepath = self.storage_dir / filename
                
                # Save image
                cv2.imwrite(str(filepath), frame)
                
                logger.info(f"Image captured: {filename}")
                return filename
                
            except Exception as e:
                logger.error(f"Camera capture failed: {e}", exc_info=True)
                raise RuntimeError(f"Camera capture failed: {e}")
            
            finally:
                if cap:
                    cap.release()