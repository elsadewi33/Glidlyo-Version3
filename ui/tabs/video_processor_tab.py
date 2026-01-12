"""Video processor tab with merge, upscale, clipper, and looping functionalities."""
import os
import subprocess
import threading
import wx
from ui.dialogs import filedialog, messagebox


class VideoProcessorTab(wx. Panel):
    """Video processor tab containing sub-tabs for different processing tools."""
    
    def __init__(self, parent, app_state):
        """Initialize the Video Processor tab.
        
        Args:
            parent: Parent window
            app_state: Dictionary containing shared application state and variables
        """
        super().__init__(parent)
        self.app_state = app_state
        
        # Create notebook for sub-tabs
        self.notebook = wx.Notebook(self)
        
        # Create sub-tabs
        self.merge_tab = MergeVideoPanel(self.notebook, app_state)
        self.upscale_tab = UpscaleVideoPanel(self.notebook, app_state)
        self.looping_tab = LoopingVideoPanel(self.notebook, app_state)
        self.clipper_tab = PlaceholderPanel(self.notebook, "Clipper")
        
        # Add tabs to notebook
        self.notebook. AddPage(self.merge_tab, "Merge Video")
        self.notebook.AddPage(self.upscale_tab, "Upscale")
        self.notebook.AddPage(self.looping_tab, "Looping Video")
        self.notebook.AddPage(self.clipper_tab, "Clipper (Coming Soon)")
        
        # Layout
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 5)
        self.SetSizer(sizer)


class MergeVideoPanel(wx.Panel):
    """Panel for merging multiple videos."""
    
    def __init__(self, parent, app_state):
        """Initialize merge video panel."""
        super().__init__(parent)
        self.app_state = app_state
        
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Title
        title = wx.StaticText(self, label="Merge Multiple Videos")
        title_font = wx.Font(12, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx. FONTWEIGHT_BOLD)
        title.SetFont(title_font)
        main_sizer. Add(title, 0, wx.ALL, 10)
        
        # Info
        info = wx.StaticText(self, label="Select multiple video files to merge them into a single video.")
        main_sizer.Add(info, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        
        # Coming soon message
        coming_soon = wx.StaticText(self, label="🚧 Coming Soon 🚧")
        coming_soon_font = wx.Font(14, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx. FONTWEIGHT_BOLD)
        coming_soon.SetFont(coming_soon_font)
        coming_soon.SetForegroundColour(wx.Colour(255, 165, 0))
        main_sizer.Add(coming_soon, 0, wx.ALIGN_CENTER | wx. ALL, 20)
        
        self.SetSizer(main_sizer)


class UpscaleVideoPanel(wx.Panel):
    """Panel for upscaling videos."""
    
    def __init__(self, parent, app_state):
        """Initialize upscale video panel."""
        super().__init__(parent)
        self.app_state = app_state
        
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Title
        title = wx.StaticText(self, label="Upscale Video Quality")
        title_font = wx.Font(12, wx. FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        title.SetFont(title_font)
        main_sizer.Add(title, 0, wx.ALL, 10)
        
        # Info
        info = wx.StaticText(self, label="Enhance video resolution using AI upscaling.")
        main_sizer.Add(info, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        
        # Coming soon message
        coming_soon = wx.StaticText(self, label="🚧 Coming Soon 🚧")
        coming_soon_font = wx.Font(14, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx. FONTWEIGHT_BOLD)
        coming_soon.SetFont(coming_soon_font)
        coming_soon.SetForegroundColour(wx.Colour(255, 165, 0))
        main_sizer.Add(coming_soon, 0, wx.ALIGN_CENTER | wx.ALL, 20)
        
        self.SetSizer(main_sizer)


class LoopingVideoPanel(wx. Panel):
    """Panel for creating looped videos."""
    
    def __init__(self, parent, app_state):
        """Initialize looping video panel."""
        super().__init__(parent)
        self.app_state = app_state
        
        # State
        self.input_video = ""
        self.output_path = ""
        self.process = None
        
        # Build UI
        self._build_ui()
    
    def _build_ui(self):
        """Build the UI components."""
        main_sizer = wx.BoxSizer(wx. VERTICAL)
        
        # Title
        title = wx.StaticText(self, label="Create Looped Video")
        title_font = wx.Font(12, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx. FONTWEIGHT_BOLD)
        title.SetFont(title_font)
        main_sizer. Add(title, 0, wx.ALL, 10)
        
        # Info
        info = wx.StaticText(self, label="Create seamlessly looped video with custom duration, resolution, and FPS.")
        main_sizer.Add(info, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        
        # Input/Output section
        io_box = wx.StaticBox(self, label="Input/Output")
        io_sizer = wx.StaticBoxSizer(io_box, wx.VERTICAL)
        
        grid = wx.FlexGridSizer(rows=2, cols=3, vgap=5, hgap=10)
        
        # Input video
        grid.Add(wx.StaticText(io_box, label="Input Video: "), 0, wx.ALIGN_CENTER_VERTICAL)
        self.input_label = wx.StaticText(io_box, label="No file selected")
        self.input_label.SetForegroundColour(wx.Colour(128, 128, 128))
        grid.Add(self.input_label, 1, wx.EXPAND)
        btn_input = wx.Button(io_box, label="Browse...")
        btn_input.Bind(wx.EVT_BUTTON, self.on_browse_input)
        grid.Add(btn_input, 0)
        
        # Output path
        grid.Add(wx.StaticText(io_box, label="Output Path:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.output_label = wx.StaticText(io_box, label="No path selected")
        self.output_label.SetForegroundColour(wx.Colour(128, 128, 128))
        grid.Add(self.output_label, 1, wx. EXPAND)
        btn_output = wx.Button(io_box, label="Browse...")
        btn_output.Bind(wx.EVT_BUTTON, self.on_browse_output)
        grid.Add(btn_output, 0)
        
        grid.AddGrowableCol(1, 1)
        io_sizer.Add(grid, 0, wx.EXPAND | wx.ALL, 5)
        
        main_sizer.Add(io_sizer, 0, wx. EXPAND | wx.ALL, 5)
        
        # Settings section
        settings_box = wx.StaticBox(self, label="Loop Settings")
        settings_sizer = wx.StaticBoxSizer(settings_box, wx. VERTICAL)
        
        grid_settings = wx.FlexGridSizer(rows=4, cols=2, vgap=5, hgap=10)
        
        # Resolution
        grid_settings.Add(wx.StaticText(settings_box, label="Resolution:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.resolution_combo = wx.ComboBox(settings_box, choices=["240p", "360p", "480p", "720p", "1080p", "1440p", "4K", "Original"], style=wx.CB_READONLY)
        self.resolution_combo.SetValue("Original")
        grid_settings. Add(self.resolution_combo, 1, wx.EXPAND)
        
        # FPS
        grid_settings.Add(wx.StaticText(settings_box, label="FPS:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.fps_combo = wx.ComboBox(settings_box, choices=["15", "24", "30", "60", "120", "Original"], style=wx.CB_READONLY)
        self.fps_combo.SetValue("Original")
        grid_settings.Add(self.fps_combo, 1, wx.EXPAND)
        
        # Loop Duration
        grid_settings.Add(wx.StaticText(settings_box, label="Loop Duration:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.loop_duration_combo = wx.ComboBox(settings_box, choices=["1 Hour", "2 Hours", "4 Hours", "8 Hours", "12 Hours", "24 Hours"], style=wx.CB_READONLY)
        self.loop_duration_combo.SetValue("1 Hour")
        grid_settings.Add(self.loop_duration_combo, 1, wx. EXPAND)
        
        # Quality preset
        grid_settings.Add(wx.StaticText(settings_box, label="Quality Preset: "), 0, wx.ALIGN_CENTER_VERTICAL)
        self.preset_combo = wx.ComboBox(settings_box, choices=["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow"], style=wx.CB_READONLY)
        self.preset_combo.SetValue("veryfast")
        grid_settings.Add(self.preset_combo, 1, wx.EXPAND)
        
        grid_settings.AddGrowableCol(1, 1)
        settings_sizer.Add(grid_settings, 0, wx.EXPAND | wx.ALL, 5)
        
        main_sizer.Add(settings_sizer, 0, wx.EXPAND | wx. ALL, 5)
        
        # Control buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.generate_btn = wx.Button(self, label="Generate Looped Video")
        self.generate_btn.SetBackgroundColour(wx.Colour(40, 167, 69))
        self.generate_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        self.generate_btn.Bind(wx.EVT_BUTTON, self.on_generate)
        btn_sizer.Add(self.generate_btn, 1, wx. EXPAND | wx.RIGHT, 5)
        
        self.cancel_btn = wx.Button(self, label="Cancel")
        self.cancel_btn.SetBackgroundColour(wx. Colour(220, 53, 69))
        self.cancel_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        self.cancel_btn. Disable()
        self.cancel_btn.Bind(wx.EVT_BUTTON, self.on_cancel)
        btn_sizer.Add(self.cancel_btn, 1, wx.EXPAND)
        
        main_sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 10)
        
        # Log area
        log_label = wx.StaticText(self, label="Processing Log:")
        main_sizer.Add(log_label, 0, wx.TOP | wx.LEFT, 10)
        
        self.log_text = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.log_text.SetBackgroundColour(wx.Colour(30, 30, 30))
        self.log_text.SetForegroundColour(wx.Colour(0, 255, 0))
        self.log_text.SetFont(wx.Font(9, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        main_sizer. Add(self.log_text, 1, wx.EXPAND | wx.ALL, 5)
        
        self.SetSizer(main_sizer)
    
    def log(self, message):
        """Log a message to the log area."""
        wx.CallAfter(self._append_log, message + "\n")
    
    def _append_log(self, message):
        """Append message to log (must be called from main thread)."""
        self.log_text.AppendText(message)
    
    def on_browse_input(self, event):
        """Handle input video browse button."""
        path = filedialog.askopenfilename(
            title="Select Input Video",
            filetypes=(("Video files", "*.mp4;*.avi;*.mov;*. mkv"), ("All files", "*.*"))
        )
        if path:
            self.input_video = path
            self.input_label.SetLabel(os.path.basename(path))
            self.input_label.SetForegroundColour(wx.Colour(0, 0, 255))
            
            # Auto-suggest output path
            if not self.output_path:
                base, ext = os.path.splitext(path)
                suggested_output = f"{base}_looped{ext}"
                self.output_path = suggested_output
                self. output_label.SetLabel(os.path.basename(suggested_output))
                self.output_label.SetForegroundColour(wx.Colour(0, 0, 255))
    
    def on_browse_output(self, event):
        """Handle output path browse button."""
        path = filedialog.asksaveasfilename(
            title="Save Looped Video As",
            defaultfile="looped_video.mp4",
            filetypes=(("MP4 files", "*.mp4"), ("All files", "*.*"))
        )
        if path:
            # Ensure . mp4 extension
            if not path.lower().endswith('.mp4'):
                path += '.mp4'
            self.output_path = path
            self.output_label. SetLabel(os.path.basename(path))
            self.output_label.SetForegroundColour(wx.Colour(0, 0, 255))
    
    def get_video_duration(self, video_path, ffmpeg_path):
        """Get video duration in seconds using ffprobe. 
        
        Args:
            video_path: Path to video file
            ffmpeg_path: Path to ffmpeg executable
        
        Returns:
            Duration in seconds (float) or None if failed
        """
        # Get ffprobe path
        ffmpeg_dir = os.path.dirname(ffmpeg_path)
        ffmpeg_name = os.path.basename(ffmpeg_path)
        
        if 'ffmpeg' in ffmpeg_name. lower():
            ffprobe_name = ffmpeg_name.replace('ffmpeg', 'ffprobe').replace('FFMPEG', 'ffprobe')
        else:
            ffprobe_name = 'ffprobe. exe' if os.name == 'nt' else 'ffprobe'
        
        ffprobe_path = os.path.join(ffmpeg_dir, ffprobe_name)
        
        if not os.path.exists(ffprobe_path):
            self.log(f"⚠️ ffprobe not found at {ffprobe_path}")
            return None
        
        cmd = [
            ffprobe_path,
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            duration = float(result.stdout.strip())
            return duration
        except Exception as e:
            self.log(f"⚠️ Failed to get video duration: {e}")
            return None
    
    def on_generate(self, event):
        """Handle generate button."""
        # Validation
        if not self.input_video or not os.path.exists(self.input_video):
            messagebox.showerror("Error", "Please select an input video file!")
            return
        
        if not self.output_path:
            messagebox.showerror("Error", "Please select an output path!")
            return
        
        # Check if output file already exists
        if os.path.exists(self.output_path):
            result = messagebox.askyesno("Confirm", f"File already exists:\n{self.output_path}\n\nOverwrite?")
            if not result:
                return
        
        self.log("=" * 50)
        self.log("🎬 Starting video loop generation...")
        self.log(f"📂 Input: {os.path.basename(self.input_video)}")
        self.log(f"💾 Output: {os.path.basename(self.output_path)}")
        
        # Get settings
        resolution = self.resolution_combo.GetValue()
        fps = self.fps_combo.GetValue()
        loop_duration = self.loop_duration_combo.GetValue()
        preset = self.preset_combo.GetValue()
        
        self.log(f"⚙️ Resolution: {resolution}")
        self.log(f"⚙️ FPS: {fps}")
        self.log(f"⚙️ Duration: {loop_duration}")
        self.log(f"⚙️ Quality Preset: {preset}")
        
        # Disable generate button, enable cancel
        self.generate_btn. Disable()
        self.cancel_btn.Enable()
        
        # Run in background thread
        def generate():
            try:
                from core.config import config
                ffmpeg_path = config.ffmpeg_path
                
                # Get video duration
                video_duration = self.get_video_duration(self.input_video, ffmpeg_path)
                
                if not video_duration: 
                    self.log("⚠️ Could not detect video duration, using default 8 seconds")
                    video_duration = 8.0
                else:
                    self.log(f"📹 Video duration: {video_duration:.2f} seconds")
                
                # Calculate loop count
                loop_duration_map = {
                    "1 Hour": 3600,
                    "2 Hours": 7200,
                    "4 Hours": 14400,
                    "8 Hours": 28800,
                    "12 Hours": 43200,
                    "24 Hours": 86400
                }
                
                target_duration = loop_duration_map.get(loop_duration, 3600)
                stream_loop_count = int(target_duration / video_duration)
                
                self.log(f"🔄 Will loop {stream_loop_count} times (~{target_duration / 3600:.1f} hours)")
                
                # Create temporary loop list file
                temp_loop_file = "temp_loop_video.txt"
                video_path_abs = os.path.abspath(self.input_video)
                
                with open(temp_loop_file, 'w') as f:
                    video_path_escaped = video_path_abs.replace('\\', '/')
                    f.write(f"file '{video_path_escaped}'\n")
                
                self.log("✅ Created loop configuration file")
                
                # Build FFmpeg command
                cmd = [
                    ffmpeg_path,
                    '-f', 'concat',
                    '-safe', '0',
                    '-stream_loop', str(stream_loop_count),
                    '-i', temp_loop_file
                ]
                
                # Video filters
                vf_filters = []
                
                # Resolution
                if resolution != "Original":
                    resolution_map = {
                        "240p": 240,
                        "360p":  360,
                        "480p": 480,
                        "720p": 720,
                        "1080p": 1080,
                        "1440p": 1440,
                        "4K": 2160
                    }
                    height = resolution_map.get(resolution, 720)
                    vf_filters.append(f'scale=-2:{height}')
                
                # FPS
                if fps != "Original":
                    vf_filters.append(f'fps={fps}')
                
                # Apply filters if any
                if vf_filters:
                    cmd.extend(['-vf', ','.join(vf_filters)])
                
                # Encoding settings
                cmd.extend([
                    '-c:v', 'libx264',
                    '-preset', preset,
                    '-crf', '23',
                    '-c:a', 'aac',
                    '-b:a', '128k',
                    '-y',  # Overwrite output
                    self.output_path
                ])
                
                self. log("🎬 Starting FFmpeg encoding...")
                self.log("⏳ This may take a while depending on duration and settings...")
                
                # Run FFmpeg
                self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                # Monitor stderr for progress
                while self.process and self.process.poll() is None:
                    line = self.process.stderr.readline()
                    if not line:
                        break
                    
                    decoded = line.decode('utf-8', errors='ignore').strip()
                    if not decoded:
                        continue
                    
                    # Log progress lines (frame=, time=, etc.)
                    if decoded.startswith('frame=') or 'time=' in decoded. lower():
                        # Extract time info for progress
                        if 'time=' in decoded: 
                            self.log(f"⏱️ {decoded}")
                
                returncode = self.process.poll()
                
                # Cleanup temp file
                if os.path. exists(temp_loop_file):
                    os.remove(temp_loop_file)
                
                if returncode == 0:
                    self.log("✅ Video loop generation completed successfully!")
                    self.log(f"💾 Output saved to: {self.output_path}")
                    wx.CallAfter(messagebox.showinfo, "Success", "Looped video generated successfully!")
                else:
                    self.log(f"❌ FFmpeg process exited with code {returncode}")
                    wx.CallAfter(messagebox.showerror, "Error", "Video generation failed.  Check the log for details.")
                
            except Exception as e:
                self.log(f"❌ Error:  {str(e)}")
                wx. CallAfter(messagebox.showerror, "Error", f"Failed to generate video:\n{str(e)}")
            
            finally:
                wx.CallAfter(self._on_complete)
        
        threading.Thread(target=generate, daemon=True).start()
    
    def on_cancel(self, event):
        """Handle cancel button."""
        if self.process:
            self.log("⏹ Cancelling process...")
            self.process.terminate()
            self.process.wait()
            self.process = None
            self.log("❌ Process cancelled by user")
        
        self._on_complete()
    
    def _on_complete(self):
        """Reset UI after completion or cancellation."""
        self.generate_btn.Enable()
        self.cancel_btn.Disable()
        self.process = None


class PlaceholderPanel(wx.Panel):
    """Placeholder panel for features coming soon."""
    
    def __init__(self, parent, feature_name):
        """Initialize placeholder panel. 
        
        Args:
            parent: Parent window
            feature_name: Name of the feature
        """
        super().__init__(parent)
        
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Title
        title = wx.StaticText(self, label=feature_name)
        title_font = wx.Font(12, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        title.SetFont(title_font)
        main_sizer.Add(title, 0, wx. ALL, 10)
        
        # Coming soon message
        coming_soon = wx.StaticText(self, label="🚧 Coming Soon 🚧")
        coming_soon_font = wx.Font(14, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx. FONTWEIGHT_BOLD)
        coming_soon.SetFont(coming_soon_font)
        coming_soon.SetForegroundColour(wx.Colour(255, 165, 0))
        main_sizer.Add(coming_soon, 0, wx. ALIGN_CENTER | wx.ALL, 20)
        
        info_text = wx.StaticText(self, label=f"{feature_name} will be available in a future update.\nStay tuned!")
        info_text.SetForegroundColour(wx. Colour(128, 128, 128))
        main_sizer.Add(info_text, 0, wx. ALIGN_CENTER | wx.ALL, 10)
        
        self.SetSizer(main_sizer)