"""Orchestration pipeline for video generation, merging, and upload."""
import os
import json
import time
from typing import Callable, Optional
from core.models import GenerationConfig
from core.logger import Logger
from core.utils import parse_prompt_item, check_processed_videos, compute_generation_status
from core.config import config
from generation.factory import create_runner
from generation.base_runner import BaseRunner
from media.ffmpeg_ops import MediaProcessor
from youtube_uploader import YoutubeUploader
from thumbnail_generator import ThumbnailGenerator


class Pipeline:
    """Main orchestration pipeline for video processing."""
    
    def __init__(self, gen_config: GenerationConfig, prompt_folder: str,
                 youtube_channels: dict, logger: Logger,
                 pause_check: Callable[[], bool], stop_check: Callable[[], bool]):
        """Initialize pipeline.
        
        Args:
            gen_config: Generation configuration
            prompt_folder: Path to folder containing JSON prompts
            youtube_channels: YouTube channel configuration
            logger: Logger instance
            pause_check: Function to check if paused
            stop_check: Function to check if stopped
        """
        self.gen_config = gen_config
        self.prompt_folder = prompt_folder
        self.youtube_channels = youtube_channels
        self.logger = logger
        self.pause_check = pause_check
        self.stop_check = stop_check
        
        # Initialize processors
        self.media_processor = MediaProcessor(
            ffmpeg_path=config.ffmpeg_path,
            assets_folder=config.assets_folder,
            music_folder=config.music_folder,
            logger=logger
        )
    
    def run(self):
        """Run the complete pipeline for all JSON files."""
        runner: Optional[BaseRunner] = None
        
        try:
            # Create appropriate runner
            runner = create_runner(self.gen_config, self.logger)
            if not runner:
                self.logger.error("Failed to create runner")
                return
            
            # Initialize runner
            if not runner.initialize():
                self.logger.error("Failed to initialize runner")
                return
            
            # Process each JSON file
            for json_file in sorted(os.listdir(self.prompt_folder)):
                if self.stop_check():
                    self.logger.log("⏹ Automation stopped by user")
                    break
                
                if not json_file.endswith(".json"):
                    continue
                
                self._process_json_file(json_file, runner)
            
            self.logger.log("🎉 ALL JSON FILES PROCESSED!")
            
        except Exception as e:
            self.logger.error(f"Pipeline error: {e}")
        finally:
            if runner:
                runner.cleanup()
    
    def _process_json_file(self, json_file: str, runner: BaseRunner):
        """Process a single JSON file.
        
        Args:
            json_file: Name of JSON file
            runner: Runner instance to use
        """
        save_dir = os.path.join(config.base_download_path, os.path.splitext(json_file)[0])
        os.makedirs(save_dir, exist_ok=True)
        
        # Load prompts
        with open(os.path.join(self.prompt_folder, json_file), 'r', encoding='utf-8') as f:
            data_json = json.load(f)
        
        total_scenes = len(data_json)
        self.logger.log("=" * 50)
        self.logger.log(f"📁 Processing: {json_file} (total scenes: {total_scenes})")
        self.logger.log(f"🧭 Generation Method: {self.gen_config.gen_method}")
        if self.gen_config.seed_image_path:
            self.logger.log(f"🖼️ Seed Image: {self.gen_config.seed_image_path}")
        
        # Check already processed scenes
        processed_scenes = check_processed_videos(save_dir, total_scenes)
        if processed_scenes:
            self.logger.log(f"⏭️ Skipping {len(processed_scenes)} already processed scenes")
        
        # Generate scenes
        last_frame_path = None
        for i, item in enumerate(data_json, 1):
            # Check pause/stop
            while self.pause_check() and not self.stop_check():
                time.sleep(1)
            if self.stop_check():
                break
            
            # Skip if already processed
            if i in processed_scenes:
                self.logger.log(f"⏭️ Scene #{i} already exists, skipping...")
                video_path = os.path.join(save_dir, f"{i}.mp4")
                if os.path.exists(video_path):
                    temp_frame = os.path.join(save_dir, f"last_frame_{i}.jpg")
                    if os.path.exists(temp_frame):
                        last_frame_path = temp_frame
                continue
            
            # Parse prompt
            scene = parse_prompt_item(item, i)
            
            # Generate scene
            result_path = runner.generate_scene(scene, save_dir, last_frame_path)
            
            # Update last frame path
            if result_path and os.path.exists(result_path):
                temp_frame = os.path.join(save_dir, f"last_frame_{i}.jpg")
                if os.path.exists(temp_frame):
                    last_frame_path = temp_frame
            else:
                last_frame_path = None
        
        # Check completion status
        status = compute_generation_status(save_dir, total_scenes)
        
        if not status.is_complete:
            self.logger.log(f"⚠️ Incomplete generation for '{json_file}'. Missing scenes: {status.missing_scenes}")
            incomplete_path = os.path.join(save_dir, "incomplete.txt")
            with open(incomplete_path, "w", encoding="utf-8") as f:
                f.write("missing=" + ",".join(map(str, status.missing_scenes)))
            self.logger.log(f"📝 Wrote {os.path.basename(incomplete_path)}. Merge is skipped.")
            return
        
        # All scenes complete - create finish marker
        with open(os.path.join(save_dir, "finish.txt"), "w", encoding="utf-8") as f:
            f.write("done")
        self.logger.log("✅ All scenes present — finish.txt created, starting post-processing...")
        
        # Post-processing: merge, upscale, upload
        self._post_process(save_dir, json_file)
    
    def _post_process(self, save_dir: str, json_file: str):
        """Post-process generated videos (merge, upscale, upload).
        
        Args:
            save_dir: Directory containing generated videos
            json_file: Name of source JSON file
        """
        current_mode = self.gen_config.mode
        final_video = None
        
        # Merge based on mode
        if current_mode == "Sound Relief":
            final_video = self.media_processor.create_sound_relief_video(
                save_dir, self.gen_config.loop_duration
            )
        elif current_mode == "Restorasi":
            final_video = self.media_processor.merge_with_intro(save_dir)
        elif self.gen_config.auto_merge:
            final_video = self.media_processor.merge_process(save_dir)
        
        # Upscale if requested
        if final_video and self.gen_config.upscale:
            upscaled = final_video.replace(".mp4", "_4K.mp4")
            if self.media_processor.upscale_video(final_video, upscaled):
                final_video = upscaled
        
        # Upload to YouTube if requested
        if final_video and self.gen_config.upload_youtube:
            video_title = f"{os.path.splitext(json_file)[0]} - {current_mode}"
            self._upload_to_youtube(final_video, video_title, current_mode)
    
    def _upload_to_youtube(self, video_path: str, title: str, mode: str):
        """Upload video to YouTube.
        
        Args:
            video_path: Path to video file
            title: Video title
            mode: Mode (for channel selection)
        """
        try:
            channel_config = self.youtube_channels.get(mode, {})
            channel_name = channel_config.get("name", "Unknown Channel")
            credentials_path = channel_config.get("credentials", "")
            
            if not credentials_path or not os.path.exists(credentials_path):
                self.logger.log(f"❌ Credentials file not found for mode '{mode}'")
                self.logger.log(f" Expected: {credentials_path}")
                return None
            
            self.logger.log(f"📤 Uploading to YouTube Channel: {channel_name}")
            self.logger.log(f" Using credentials: {os.path.basename(credentials_path)}")
            
            uploader = YoutubeUploader(config.client_secrets, credentials_path)
            description = f"Video generated using Glidly Pro AI Automator\nMode: {mode}\nChannel: {channel_name}"
            tags = "AI,automation,video"
            
            thumbnail_path = None
            if mode == "Restorasi":
                self.logger.log("🖼️ Generating thumbnail...")
                thumb_gen = ThumbnailGenerator()
                thumbnail_path = video_path.replace(".mp4", "_thumbnail.jpg")
                thumb_gen.generate(video_path, thumbnail_path)
            
            video_id = uploader.upload_video(
                file_path=video_path,
                title=title,
                description=description,
                tags=tags,
                category_id=mode.lower().replace(" ", "_"),
                thumbnail_path=thumbnail_path
            )
            
            self.logger.log(f"✅ YouTube Upload Complete!")
            self.logger.log(f" Channel: {channel_name}")
            self.logger.log(f" Video ID: {video_id}")
            self.logger.log(f" URL: https://youtube.com/watch?v={video_id}")
            return video_id
            
        except Exception as e:
            self.logger.log(f"❌ YouTube Upload Failed: {str(e)}")
            return None
