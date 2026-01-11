"""Variable wrapper for compatibility with Tkinter-like interface."""


class SimpleVar:
    """Simple variable wrapper with get/set methods."""
    
    def __init__(self, value=None):
        """Initialize with optional value.
        
        Args:
            value: Initial value
        """
        self._value = value
    
    def get(self):
        """Get the current value.
        
        Returns:
            Current value
        """
        return self._value
    
    def set(self, v):
        """Set a new value.
        
        Args:
            v: New value
        """
        self._value = v
