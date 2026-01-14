"""Shared data models and structures."""
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class GenerationConfig:
    """Configuration for video generation."""
    prompt_folder: str  # Folder containing JSON prompts
    mode: str  # Shorts, Sound Relief, Restorasi, Home Renovation
    generator: str  # Veo 3.1, Nexa Gen, Sora 2
    timeout: int  # seconds
    auto_merge: bool
    upscale: bool
    upload_youtube: bool
    loop_duration: int  # for Sound Relief mode
    gen_method: str  # Default, Flow, Google Flow
    seed_image_path: Optional[str] = None
    subcategory: str = "Default"  # Default, Nexa, Flow Video Generator, Google Flow
    video_gen_subcategory: str = "Default"  # Alias for subcategory
    google_flow_username: Optional[str] = None
    google_flow_password: Optional[str] = None
    youtube_channels: Optional[Dict[str, Dict[str, str]]] = None  # Channel mapping per mode


@dataclass
class ScenePrompt:
    """Represents a scene prompt (can be dict or string)."""
    index: int
    prompt_text: str
    raw_data: Any  # Original data from JSON


@dataclass
class ProcessingStatus:
    """Status of video processing."""
    total_scenes: int
    processed_scenes: set
    missing_scenes: list
    is_complete: bool
