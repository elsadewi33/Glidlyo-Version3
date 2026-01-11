"""Base class for video generation runners."""
from abc import ABC, abstractmethod
from typing import Optional
from core.models import GenerationConfig, ScenePrompt
from core.logger import Logger


class BaseRunner(ABC):
    """Abstract base class for video generation runners."""
    
    def __init__(self, config: GenerationConfig, logger: Logger):
        """Initialize runner.
        
        Args:
            config: Generation configuration
            logger: Logger instance
        """
        self.config = config
        self.logger = logger
        self.is_running = False
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the runner (e.g., open browser, login).
        
        Returns:
            True if initialization successful, False otherwise
        """
        pass
    
    @abstractmethod
    def generate_scene(self, scene: ScenePrompt, save_dir: str, 
                      last_frame_path: Optional[str] = None) -> Optional[str]:
        """Generate a single scene.
        
        Args:
            scene: Scene prompt data
            save_dir: Directory to save the generated video
            last_frame_path: Path to last frame from previous scene (for I2V)
        
        Returns:
            Path to generated video if successful, None otherwise
        """
        pass
    
    @abstractmethod
    def cleanup(self):
        """Clean up resources (e.g., close browser)."""
        pass
    
    def stop(self):
        """Stop the runner."""
        self.is_running = False
