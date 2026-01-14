"""Utility functions for prompt parsing and status computation."""
import os
import re
from typing import Dict, List, Tuple, Set, Any
from core.models import ScenePrompt, ProcessingStatus


def parse_prompt_item(item: Any, index: int) -> ScenePrompt:
    """Parse a prompt item from JSON data.
    
    Args:
        item: Prompt data (dict or string)
        index: Scene index (1-based)
    
    Returns:
        ScenePrompt object
    """
    if isinstance(item, dict):
        prompt_parts = [
            item.get("car_identity", ""),
            item.get("character", ""),
            item.get("action_description", ""),
            item.get("environment", ""),
            item.get("camera", ""),
            item.get("visual_style", "")
        ]
        prompt_text = " ".join([p for p in prompt_parts if p])
    else:
        prompt_text = str(item)
    
    return ScenePrompt(index=index, prompt_text=prompt_text, raw_data=item)


def check_processed_videos(folder_path: str, total_prompts: int) -> Set[int]:
    """Check which videos have already been processed.
    
    Args:
        folder_path: Directory containing processed videos
        total_prompts: Total number of prompts/scenes
    
    Returns:
        Set of processed scene indices
    """
    processed = set()
    if not os.path.exists(folder_path):
        return processed
    
    for filename in os.listdir(folder_path):
        if filename.endswith(".mp4") and filename.split('.')[0].isdigit():
            scene_id = int(filename.split('.')[0])
            if scene_id <= total_prompts:
                processed.add(scene_id)
    
    return processed


def compute_generation_status(folder_path: str, total_prompts: int) -> ProcessingStatus:
    """Compute generation status for a folder.
    
    Args:
        folder_path: Directory containing generated videos
        total_prompts: Total number of expected scenes
    
    Returns:
        ProcessingStatus object
    """
    present = set()
    
    if os.path.exists(folder_path):
        for filename in os.listdir(folder_path):
            if re.match(r'^\d+\.mp4$', filename):
                present.add(int(filename.split('.')[0]))
    
    missing = [i for i in range(1, total_prompts + 1) if i not in present]
    is_complete = len(missing) == 0
    
    return ProcessingStatus(
        total_scenes=total_prompts,
        processed_scenes=present,
        missing_scenes=missing,
        is_complete=is_complete
    )
