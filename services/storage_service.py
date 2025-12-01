"""
Local Storage Service
Manages local file storage for images and data
"""
import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class StorageService:
    """Local file storage manager"""
    
    def __init__(self, base_dir: str = "web/static/images"):
        """
        Initialize storage service
        
        Args:
            base_dir: Base directory for file storage
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Storage service initialized: {self.base_dir}")
    
    def list_images(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        List captured images
        
        Args:
            limit: Maximum number of images to return
        
        Returns:
            List of image metadata dictionaries
        """
        try:
            images = sorted(
                self.base_dir.glob("*.jpg"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )[:limit]
            
            return [
                {
                    'filename': img.name,
                    'timestamp': img.stat().st_mtime,
                    'size': img.stat().st_size
                }
                for img in images
            ]
            
        except Exception as e:
            logger.error(f"Failed to list images: {e}")
            return []
    
    def delete_old_images(self, max_count: int = 1000):
        """
        Delete old images to free space
        
        Args:
            max_count: Maximum number of images to keep
        """
        try:
            images = sorted(
                self.base_dir.glob("*.jpg"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            
            if len(images) > max_count:
                for img in images[max_count:]:
                    img.unlink()
                    logger.info(f"Deleted old image: {img.name}")
                    
        except Exception as e:
            logger.error(f"Failed to delete old images: {e}")