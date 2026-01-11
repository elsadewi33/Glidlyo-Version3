"""Flow video generation runner using FlowEditorRunner."""
import os
import subprocess
from typing import Optional
from generation.base_runner import BaseRunner
from core.models import GenerationConfig, ScenePrompt
from core.logger import Logger
from flow_editor_runner import FlowEditorRunner


class FlowRunner(BaseRunner):
    """Flow runner using FlowEditorRunner for video generation."""
    
    def __init__(self, config: GenerationConfig, logger: Logger,
                 email: str, password: str, ffmpeg_path: str, timeout: int,
                 extensions_root: str, user_data_dir: str, download_dir: str,
                 headless: bool, start_account_index: int, preferred_ext_id: Optional[str] = None):
        """Initialize Flow runner.
        
        Args:
            config: Generation configuration
            logger: Logger instance
            email: Login email
            password: Login password
            ffmpeg_path: Path to ffmpeg executable
            timeout: Timeout in seconds
            extensions_root: Path to extensions root folder
            user_data_dir: Path to user data directory
            download_dir: Path to download directory
            headless: Whether to run in headless mode
            start_account_index: Starting account index
            preferred_ext_id: Preferred extension ID (optional)
        """
        super().__init__(config, logger)
        self.email = email
        self.password = password
        self.ffmpeg_path = ffmpeg_path
        self.timeout = timeout
        self.extensions_root = extensions_root
        self.user_data_dir = user_data_dir
        self.download_dir = download_dir
        self.headless = headless
        self.start_account_index = start_account_index
        self.preferred_ext_id = preferred_ext_id
        self.runner = None
    
    def initialize(self) -> bool:
        """Initialize Flow runner and open editor."""
        try:
            self.runner = FlowEditorRunner(
                email=self.email,
                password=self.password,
                extensions_root=self.extensions_root,
                user_data_dir=self.user_data_dir,
                download_dir=self.download_dir,
                headless=self.headless,
                start_account_index=self.start_account_index,
                timeout_ms=self.timeout * 1000,
                preferred_ext_id=self.preferred_ext_id,
                keep_popup_open=True,
                log_fn=self.logger.log,
            )
            
            self.runner.start_context()
            self.runner.open_extension_popup()
            self.runner.handle_login_prompt_if_any()
            self.runner.launch_flow_dashboard(self.runner.account_idx)
            self.runner.open_project_and_wait_editor()
            
            # Apply settings
            vertical = True if self.config.mode == "Shorts" else False
            self.runner.apply_one_time_settings(vertical=vertical)
            
            self.is_running = True
            return True
            
        except Exception as e:
            self.logger.error(f"Flow initialization failed: {e}")
            return False
    
    def generate_scene(self, scene: ScenePrompt, save_dir: str, 
                      last_frame_path: Optional[str] = None) -> Optional[str]:
        """Generate a single scene using Flow.
        
        Args:
            scene: Scene prompt data
            save_dir: Directory to save the generated video
            last_frame_path: Path to last frame from previous scene (for I2V)
        
        Returns:
            Path to generated video if successful, None otherwise
        """
        if not self.runner or not self.is_running:
            return None
        
        try:
            # Determine guide image
            guide_image = None
            if last_frame_path and os.path.exists(last_frame_path) and scene.index > 1:
                guide_image = last_frame_path
            elif scene.index == 1 and self.config.seed_image_path:
                guide_image = self.config.seed_image_path
            
            self.logger.log(f"🎬 Scene #{scene.index}: Flow generating...")
            result_path = self.runner.generate_scene(
                scene_index=scene.index,
                prompt_text=scene.prompt_text,
                guide_image=guide_image,
                save_dir=save_dir,
                max_retries=3,
            )
            
            # If failed, try rotating account
            if not result_path or not os.path.exists(result_path):
                self.logger.log("🔁 Scene failed after 3 tries — rotating account & retrying...")
                self.runner.rotate_account_and_reopen_editor()
                vertical = True if self.config.mode == "Shorts" else False
                self.runner.apply_one_time_settings(vertical=vertical)
                result_path = self.runner.generate_scene(
                    scene_index=scene.index,
                    prompt_text=scene.prompt_text,
                    guide_image=guide_image,
                    save_dir=save_dir,
                    max_retries=3,
                )
            
            # Extract last frame if successful
            if result_path and os.path.exists(result_path):
                temp_frame = os.path.join(save_dir, f"last_frame_{scene.index}.jpg")
                subprocess.run([self.ffmpeg_path, '-sseof', '-1', '-i', result_path,
                               '-update', '1', '-q:v', '2', '-frames:v', '1',
                               temp_frame, '-y'],
                              stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
                self.logger.log(f"✅ Scene #{scene.index}: Flow SUCCESS")
                return result_path
            else:
                self.logger.log(f"❌ Scene #{scene.index}: Flow FAILED after rotation")
                return None
                
        except Exception as e:
            self.logger.error(f"Scene #{scene.index} generation error: {e}")
            return None
    
    def cleanup(self):
        """Close Flow runner and cleanup resources."""
        if self.runner:
            self.runner.close()
            self.runner = None
        self.is_running = False
