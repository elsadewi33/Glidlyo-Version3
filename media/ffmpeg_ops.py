"""FFmpeg-based media operations for video processing."""
import os
import subprocess
import re
import random
from typing import Optional
from core.logger import Logger


class MediaProcessor:
    """Handles all FFmpeg-based video operations."""
    
    def __init__(self, ffmpeg_path: str, assets_folder: str, music_folder: str, logger: Logger):
        """Initialize media processor.
        
        Args:
            ffmpeg_path: Path to ffmpeg executable
            assets_folder: Path to assets folder
            music_folder: Path to music folder
            logger: Logger instance for logging
        """
        self.ffmpeg_path = ffmpeg_path
        self.assets_folder = assets_folder
        self.music_folder = music_folder
        self.logger = logger
    
    def upscale_video(self, input_path: str, output_path: str) -> Optional[str]:
        """Upscale video to 4K resolution.
        
        Args:
            input_path: Input video path
            output_path: Output video path
        
        Returns:
            Output path if successful, None otherwise
        """
        self.logger.log("🔍 Upscaling video to 4K...")
        cmd = [
            self.ffmpeg_path, '-i', input_path,
            '-vf', 'scale=3840:2160:flags=lanczos',
            '-c:v', 'libx264', '-preset', 'slow', '-crf', '18',
            '-c:a', 'copy',
            output_path, '-y'
        ]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            self.logger.log(f"✅ Upscale Success: {os.path.basename(output_path)}")
            return output_path
        except Exception as e:
            self.logger.log(f"❌ Upscale Failed: {e}")
            return None
    
    def merge_process(self, folder_path: str) -> Optional[str]:
        """Merge video files in folder.
        
        Args:
            folder_path: Path to folder containing numbered video files
        
        Returns:
            Path to merged video if successful, None otherwise
        """
        video_files = sorted([f for f in os.listdir(folder_path)
                              if f.endswith(".mp4") and f.split('.')[0].isdigit()],
                             key=lambda x: int(x.split('.')[0]))
        if not video_files:
            return None
        
        list_path = os.path.join(folder_path, "ffmpeg_list.txt")
        with open(list_path, "w") as f:
            for v in video_files:
                f.write(f"file '{v}'\n")
        
        output_path = os.path.join(folder_path, "FINAL_MERGED_VIDEO.mp4")
        cmd = [self.ffmpeg_path, '-f', 'concat', '-safe', '0', '-i', list_path,
               '-c', 'copy', output_path, '-y']
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            self.logger.log(f"✅ Merge Success: {os.path.basename(output_path)}")
            if os.path.exists(list_path):
                os.remove(list_path)
            return output_path
        except Exception as e:
            self.logger.log(f"❌ Merge Failed: {e}")
            return None
    
    def merge_with_intro(self, folder_path: str) -> Optional[str]:
        """Merge videos with intro video at the beginning.
        
        Args:
            folder_path: Path to folder containing numbered video files
        
        Returns:
            Path to merged video if successful, None otherwise
        """
        intro_path = os.path.join(self.assets_folder, "intro.mp4")
        if not os.path.exists(intro_path):
            self.logger.log("⚠️ intro.mp4 not found in Assets folder, skipping intro")
            return self.merge_process(folder_path)
        
        video_files = sorted([f for f in os.listdir(folder_path)
                              if f.endswith(".mp4") and f.split('.')[0].isdigit()],
                             key=lambda x: int(x.split('.')[0]))
        if not video_files:
            return None
        
        list_path = os.path.join(folder_path, "ffmpeg_list_with_intro.txt")
        with open(list_path, "w") as f:
            f.write(f"file '{intro_path}'\n")
            for v in video_files:
                f.write(f"file '{os.path.join(folder_path, v)}'\n")
        
        output_path = os.path.join(folder_path, "FINAL_MERGED_VIDEO.mp4")
        cmd = [self.ffmpeg_path, '-f', 'concat', '-safe', '0', '-i', list_path,
               '-c', 'copy', output_path, '-y']
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            self.logger.log(f"✅ Merged with intro: {os.path.basename(output_path)}")
            if os.path.exists(list_path):
                os.remove(list_path)
            return output_path
        except Exception as e:
            self.logger.log(f"❌ Merge Failed: {e}")
            return None
    
    def create_sound_relief_video(self, folder_path: str, duration_minutes: int) -> Optional[str]:
        """Create Sound Relief video with looping and music.
        
        Args:
            folder_path: Path to folder containing video files
            duration_minutes: Target duration in minutes
        
        Returns:
            Path to created video if successful, None otherwise
        """
        self.logger.log(f"🎵 Creating Sound Relief video ({duration_minutes} minutes)...")
        video_files = sorted([f for f in os.listdir(folder_path)
                              if f.endswith(".mp4") and f.split('.')[0].isdigit()],
                             key=lambda x: int(x.split('.')[0]))
        if not video_files:
            self.logger.log("❌ No video files found for Sound Relief")
            return None
        
        # Create base sequence
        list_path = os.path.join(folder_path, "temp_concat.txt")
        with open(list_path, "w") as f:
            for v in video_files:
                f.write(f"file '{v}'\n")
        
        base_video = os.path.join(folder_path, "base_sequence.mp4")
        subprocess.run([
            self.ffmpeg_path, '-f', 'concat', '-safe', '0', '-i', list_path,
            '-c', 'copy', base_video, '-y'
        ], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        
        # Get base video duration
        probe_cmd = [self.ffmpeg_path, '-i', base_video, '-f', 'null', '-']
        result = subprocess.run(probe_cmd, capture_output=True, text=True)
        duration_match = re.search(r'Duration:\s+(\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?', result.stderr)
        base_duration_sec = 10
        if duration_match:
            h, m, s = map(int, duration_match.groups()[:3])
            frac = duration_match.group(4)
            base_duration_sec = h * 3600 + m * 60 + s + (int(frac) / (10 ** len(frac)) if frac else 0)
        
        # Calculate loop count
        target_duration_sec = duration_minutes * 60
        loop_count = max(1, int(target_duration_sec / base_duration_sec) + 1)
        
        # Create looped video
        looped_video = os.path.join(folder_path, "looped_video.mp4")
        subprocess.run([
            self.ffmpeg_path, '-stream_loop', str(loop_count - 1), '-i', base_video,
            '-filter_complex', f'concat=n={loop_count}:v=1:a=0,trim=duration={target_duration_sec}[v]',
            '-map', '[v]', '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
            looped_video, '-y'
        ], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        
        # Add music
        music_dir = self.music_folder
        music_files = [f for f in os.listdir(music_dir) if f.lower().endswith('.mp3')] if os.path.exists(music_dir) else []
        
        if music_files:
            music_path = os.path.join(music_dir, random.choice(music_files))
            final_output = os.path.join(folder_path, "FINAL_SOUND_RELIEF.mp4")
            self.logger.log(f"🎶 Adding music from {music_dir}: {os.path.basename(music_path)}")
            subprocess.run([
                self.ffmpeg_path, '-i', looped_video, '-stream_loop', '-1', '-i', music_path,
                '-shortest', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
                final_output, '-y'
            ], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            if os.path.exists(looped_video):
                os.remove(looped_video)
        else:
            final_output = looped_video
            self.logger.log(f"⚠️ No music files found in {music_dir}")
        
        # Cleanup
        if os.path.exists(list_path):
            os.remove(list_path)
        if os.path.exists(base_video):
            os.remove(base_video)
        
        self.logger.log(f"✅ Sound Relief video created: {os.path.basename(final_output)}")
        return final_output
