"""Logging and progress event system."""
import time
from typing import Callable, Optional


class Logger:
    """Simple logger that can send log messages to a callback."""
    
    def __init__(self, log_callback: Optional[Callable[[str], None]] = None):
        """Initialize logger with optional callback.
        
        Args:
            log_callback: Function to call with log messages (e.g., UI update function)
        """
        self.log_callback = log_callback
    
    def log(self, message: str):
        """Log a message with timestamp.
        
        Args:
            message: Message to log
        """
        timestamp = time.strftime('%H:%M:%S')
        formatted_msg = f"[{timestamp}] {message}"
        
        if self.log_callback:
            self.log_callback(formatted_msg)
        else:
            print(formatted_msg)
    
    def info(self, message: str):
        """Log an info message."""
        self.log(f"ℹ️ {message}")
    
    def success(self, message: str):
        """Log a success message."""
        self.log(f"✅ {message}")
    
    def warning(self, message: str):
        """Log a warning message."""
        self.log(f"⚠️ {message}")
    
    def error(self, message: str):
        """Log an error message."""
        self.log(f"❌ {message}")
