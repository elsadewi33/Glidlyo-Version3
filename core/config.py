"""Configuration and environment variable loading."""
import os
from dotenv import load_dotenv


class Config:
    """Application configuration loaded from environment variables."""
    
    def __init__(self):
        """Load configuration from .env file and environment variables."""
        load_dotenv()
        
        # Authentication
        self.email = os.getenv("GLID_EMAIL")
        self.pwd = os.getenv("GLID_PWD")
        
        # Paths
        self.download_path = os.path.normpath(os.getenv("DOWNLOAD_PATH")) if os.getenv("DOWNLOAD_PATH") else None
        self.base_download_path = self.download_path  # Alias for backwards compatibility
        self.ffmpeg_path = os.path.normpath(os.getenv("FFMPEG_EXE")) if os.getenv("FFMPEG_EXE") else "ffmpeg"
        self.assets_folder = os.path.normpath(os.getenv("ASSETS_FOLDER", "./Assets"))
        self.music_folder = os.path.normpath(os.getenv("MUSIC_FOLDER", os.path.join(self.assets_folder, "music")))
        
        # YouTube API
        self.client_secrets = os.getenv("YT_CLIENT_SECRETS", "client_secrets.json")
        self.credentials_file = os.getenv("YT_CREDENTIALS", "token.json")
        
        # Flow settings
        self.flow_extensions_root = os.getenv("FLOW_EXTENSIONS_ROOT", os.path.abspath("Extensions"))
        self.flow_user_data_dir = os.getenv("FLOW_USER_DATA_DIR", os.path.abspath("UserDataFlow"))
        self.flow_headless = os.getenv("FLOW_HEADLESS", "False").lower() in ("1", "true", "yes")
        self.flow_account_start = int(os.getenv("FLOW_ACCOUNT_START", "8"))
        self.flow_ext_id = os.getenv("FLOW_EXT_ID")


# Global config instance
config = Config()
