"""Livestream tab with YouTube streaming capabilities."""
import os
import configparser
import subprocess
import threading
import wx
from datetime import datetime, timedelta, timezone
from ui.dialogs import filedialog, messagebox


class LivestreamTab(wx.Panel):
    """Livestream tab containing sub-tabs for different platforms."""
    
    def __init__(self, parent, app_state):
        """Initialize the Livestream tab.   
        
        Args:  
            parent: Parent window
            app_state: Dictionary containing shared application state and variables
        """
        super().__init__(parent)
        self.app_state = app_state
        
        # Create notebook for sub-tabs
        self.notebook = wx.Notebook(self)
        
        # Create sub-tabs
        self.youtube_tab = YouTubeLivestreamPanel(self.notebook, app_state)
        self.facebook_tab = PlaceholderLivestreamPanel(self.notebook, "Facebook")
        self.tiktok_tab = PlaceholderLivestreamPanel(self.notebook, "TikTok")
        self.instagram_tab = PlaceholderLivestreamPanel(self.notebook, "Instagram")
        
        # Add tabs to notebook
        self.notebook. AddPage(self.youtube_tab, "YouTube")
        self.notebook.AddPage(self.facebook_tab, "Facebook")
        self.notebook.AddPage(self.tiktok_tab, "TikTok")
        self.notebook.AddPage(self. instagram_tab, "Instagram")
        
        # Layout
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 5)
        self.SetSizer(sizer)


class YouTubeLivestreamPanel(wx.Panel):
    """YouTube livestream panel with authentication and streaming controls."""
    
    def __init__(self, parent, app_state):
        """Initialize YouTube livestream panel."""
        super().__init__(parent)
        self.app_state = app_state
        
        # Config file path
        self.config_file = "livestream_config.ini"
        
        # Load config
        self.config = configparser.ConfigParser()
        self.load_config()
        
        # State variables
        self.authenticated = False
        self.broadcast_id = None
        self.stream_process = None
        self.rtmp_url = None
        self.temp_loop_file = None
        
        # Build UI
        self._build_ui()
    
    def _build_ui(self):
        """Build the UI components."""
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Title
        title = wx.StaticText(self, label="YouTube Livestream")
        title_font = wx.Font(12, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        title.SetFont(title_font)
        main_sizer.Add(title, 0, wx. ALL, 10)
        
        # Configuration section
        config_box = wx.StaticBox(self, label="Configuration")
        config_sizer = wx.StaticBoxSizer(config_box, wx.VERTICAL)
        
        grid = wx.FlexGridSizer(rows=3, cols=3, vgap=5, hgap=10)
        
        # Client secret file
        grid.Add(wx.StaticText(config_box, label="Client Secret: "), 0, wx.ALIGN_CENTER_VERTICAL)
        self.client_secret_label = wx.StaticText(config_box, label=os.path.basename(self.config. get('paths', 'client_secret_path', fallback='Not set')))
        self.client_secret_label.SetForegroundColour(wx. Colour(0, 0, 255))
        grid.Add(self.client_secret_label, 1, wx.EXPAND)
        btn_client_secret = wx.Button(config_box, label="Browse...")
        btn_client_secret.Bind(wx.EVT_BUTTON, self.on_browse_client_secret)
        grid.Add(btn_client_secret, 0)
        
        # Token path
        grid.Add(wx. StaticText(config_box, label="Token Path:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.token_label = wx.StaticText(config_box, label=self.config.get('paths', 'token_path', fallback='token_livestream. json'))
        self.token_label.SetForegroundColour(wx.Colour(0, 0, 255))
        grid.Add(self.token_label, 1, wx.EXPAND)
        grid.AddSpacer(0)
        
        # Video file
        grid.Add(wx.StaticText(config_box, label="Video File:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.video_label = wx.StaticText(config_box, label=os.path.basename(self.config.get('paths', 'last_video_path', fallback='Not set')))
        self.video_label.SetForegroundColour(wx.Colour(0, 0, 255))
        grid.Add(self. video_label, 1, wx.EXPAND)
        btn_video = wx.Button(config_box, label="Browse...")
        btn_video.Bind(wx.EVT_BUTTON, self.on_browse_video)
        grid.Add(btn_video, 0)
        
        grid.AddGrowableCol(1, 1)
        config_sizer.Add(grid, 0, wx.EXPAND | wx. ALL, 5)
        
        main_sizer.Add(config_sizer, 0, wx. EXPAND | wx.ALL, 5)
        
        # Broadcast metadata section
        metadata_box = wx.StaticBox(self, label="Broadcast Settings")
        metadata_sizer = wx.StaticBoxSizer(metadata_box, wx.VERTICAL)
        
        grid_meta = wx.FlexGridSizer(rows=7, cols=2, vgap=5, hgap=10)
        
        # Title
        grid_meta.Add(wx.StaticText(metadata_box, label="Title:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.title_ctrl = wx.TextCtrl(metadata_box, value="My Livestream")
        grid_meta.Add(self.title_ctrl, 1, wx.EXPAND)
        
        # Description
        grid_meta.Add(wx.StaticText(metadata_box, label="Description:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.desc_ctrl = wx.TextCtrl(metadata_box, value="Streamed via Glidly Pro", style=wx.TE_MULTILINE, size=(-1, 60))
        grid_meta.Add(self.desc_ctrl, 1, wx.EXPAND)
        
        # Privacy
        grid_meta.Add(wx.StaticText(metadata_box, label="Privacy:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.privacy_combo = wx.ComboBox(metadata_box, choices=["public", "unlisted", "private"], style=wx.CB_READONLY)
        self.privacy_combo.SetValue("public")
        grid_meta.Add(self.privacy_combo, 1, wx.EXPAND)
        
        # Start delay
        grid_meta.Add(wx.StaticText(metadata_box, label="Start Delay (min):"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.delay_spin = wx.SpinCtrl(metadata_box, min=1, max=60, initial=5)
        grid_meta.Add(self.delay_spin, 0)
        
        # Resolution
        grid_meta.Add(wx.StaticText(metadata_box, label="Resolution:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.resolution_combo = wx.ComboBox(metadata_box, choices=["240p", "360p", "480p", "720p", "1080p", "1440p", "4K"], style=wx.CB_READONLY)
        self.resolution_combo.SetValue("720p")
        grid_meta.Add(self.resolution_combo, 1, wx.EXPAND)
        
        # FPS
        grid_meta.Add(wx.StaticText(metadata_box, label="FPS: "), 0, wx.ALIGN_CENTER_VERTICAL)
        self.fps_combo = wx.ComboBox(metadata_box, choices=["15", "24", "30", "60", "120"], style=wx. CB_READONLY)
        self.fps_combo.SetValue("30")
        grid_meta.Add(self.fps_combo, 1, wx.EXPAND)
        
        # Loop Duration
        grid_meta.Add(wx.StaticText(metadata_box, label="Loop Duration: "), 0, wx.ALIGN_CENTER_VERTICAL)
        self.loop_duration_combo = wx.ComboBox(metadata_box, choices=["1 Hour", "2 Hours", "4 Hours", "8 Hours", "Forever"], style=wx.CB_READONLY)
        self.loop_duration_combo.SetValue("Forever")
        grid_meta.Add(self.loop_duration_combo, 1, wx.EXPAND)
        
        grid_meta.AddGrowableCol(1, 1)
        metadata_sizer.Add(grid_meta, 0, wx.EXPAND | wx.ALL, 5)
        
        main_sizer.Add(metadata_sizer, 0, wx. EXPAND | wx.ALL, 5)
        
        # Control buttons
        control_panel = wx.Panel(self)
        control_sizer = wx. GridSizer(rows=4, cols=3, vgap=5, hgap=5)
        
        # Row 1: Auth, Create, Start Video
        self.auth_btn = wx.Button(control_panel, label="Authenticate")
        self.auth_btn.Bind(wx.EVT_BUTTON, self.on_authenticate)
        control_sizer. Add(self.auth_btn, 0, wx. EXPAND)
        
        self. create_btn = wx.Button(control_panel, label="Create Broadcast")
        self.create_btn.Disable()
        self.create_btn.Bind(wx.EVT_BUTTON, self.on_create_broadcast)
        control_sizer.Add(self.create_btn, 0, wx. EXPAND)
        
        self.start_video_btn = wx.Button(control_panel, label="Start Video Stream")
        self.start_video_btn.Disable()
        self.start_video_btn. Bind(wx.EVT_BUTTON, self.on_start_video)
        control_sizer.Add(self.start_video_btn, 0, wx.EXPAND)
        
        # Row 2: Test Live, Check, Stop
        self.test_live_btn = wx.Button(control_panel, label="Test Live")
        self.test_live_btn.Disable()
        self.test_live_btn.SetBackgroundColour(wx.Colour(255, 193, 7))
        self.test_live_btn.SetForegroundColour(wx. Colour(0, 0, 0))
        self.test_live_btn. Bind(wx.EVT_BUTTON, self.on_test_live)
        control_sizer.Add(self.test_live_btn, 0, wx. EXPAND)
        
        self.check_btn = wx.Button(control_panel, label="Check Connection")
        self.check_btn.Disable()
        self.check_btn. Bind(wx.EVT_BUTTON, self.on_check_connection)
        control_sizer.Add(self.check_btn, 0, wx.EXPAND)
        
        self.stop_btn = wx.Button(control_panel, label="Stop Stream")
        self.stop_btn.Disable()
        self.stop_btn.Bind(wx.EVT_BUTTON, self.on_stop_stream)
        control_sizer.Add(self.stop_btn, 0, wx.EXPAND)
        
        # Row 3: Go Live
        self.go_live_btn = wx.Button(control_panel, label="🔴 GO LIVE")
        self.go_live_btn.Disable()
        self.go_live_btn.SetBackgroundColour(wx. Colour(220, 53, 69))
        self.go_live_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        self.go_live_btn.SetFont(wx.Font(10, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.go_live_btn. Bind(wx.EVT_BUTTON, self.on_go_live)
        control_sizer.Add(self.go_live_btn, 0, wx. EXPAND)
        control_sizer.AddSpacer(0)
        control_sizer.AddSpacer(0)
        
        # Row 4: Status button
        self.status_btn = wx.Button(control_panel, label="Status:  Not Authenticated")
        self.status_btn.Disable()
        control_sizer.Add(self. status_btn, 0, wx.EXPAND)
        control_sizer.AddSpacer(0)
        control_sizer.AddSpacer(0)
        
        control_panel.SetSizer(control_sizer)
        main_sizer.Add(control_panel, 0, wx. EXPAND | wx.ALL, 5)
        
        # Log area
        log_label = wx.StaticText(self, label="Livestream Activity Log:")
        main_sizer.Add(log_label, 0, wx.TOP | wx.LEFT, 10)
        
        self.log_text = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.log_text.SetBackgroundColour(wx.Colour(30, 30, 30))
        self.log_text.SetForegroundColour(wx.Colour(0, 255, 0))
        self.log_text.SetFont(wx.Font(9, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        main_sizer. Add(self.log_text, 1, wx.EXPAND | wx.ALL, 5)
        
        self.SetSizer(main_sizer)
    
    def load_config(self):
        """Load configuration from config file."""
        if os.path.exists(self. config_file):
            self.config. read(self.config_file)
        else:
            # Create default config
            self.config['paths'] = {
                'client_secret_path': '',
                'token_path': 'token_livestream.json',
                'last_video_path': ''
            }
            self.save_config()
    
    def save_config(self):
        """Save configuration to config file."""
        with open(self.config_file, 'w') as f:
            self.config.write(f)
        self.log("✅ Configuration saved")
    
    def log(self, message):
        """Log a message to the log area."""
        wx.CallAfter(self._append_log, message + "\n")
    
    def _append_log(self, message):
        """Append message to log (must be called from main thread)."""
        self.log_text.AppendText(message)
    
    def get_video_duration(self, video_path, ffmpeg_path):
        """Get video duration in seconds using ffprobe. 
        
        Args: 
            video_path: Path to video file
            ffmpeg_path: Path to ffmpeg executable
        
        Returns:
            Duration in seconds (float) or None if failed
        """
        # Get ffprobe path (same directory as ffmpeg, just different filename)
        ffmpeg_dir = os.path.dirname(ffmpeg_path)
        ffprobe_name = 'ffprobe. exe' if ffmpeg_path. endswith('.exe') else 'ffprobe'
        ffprobe_path = os.path. join(ffmpeg_dir, ffprobe_name)
        
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
    
    def on_browse_client_secret(self, event):
        """Handle client secret browse button."""
        path = filedialog.askopenfilename(
            title="Select Client Secret JSON",
            filetypes=(("JSON files", "*.json"), ("All files", "*.*"))
        )
        if path:
            self.config['paths']['client_secret_path'] = path
            self.client_secret_label.SetLabel(os.path.basename(path))
            self.save_config()
    
    def on_browse_video(self, event):
        """Handle video file browse button."""
        path = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=(("Video files", "*.mp4;*.avi;*.mov;*. mkv"), ("All files", "*.*"))
        )
        if path:
            self.config['paths']['last_video_path'] = path
            self.video_label.SetLabel(os.path.basename(path))
            self.save_config()
    
    def on_authenticate(self, event):
        """Handle authenticate button."""
        client_secret = self.config. get('paths', 'client_secret_path', fallback='')
        if not client_secret or not os.path.exists(client_secret):
            messagebox.showerror("Error", "Please select a valid client secret file first!")
            return
        
        self.log("🔐 Authenticating with YouTube...")
        
        # Run authentication in background thread
        def authenticate():
            try:
                # Lazy import Google API libraries
                try:
                    from google.oauth2.credentials import Credentials
                    from google_auth_oauthlib.flow import InstalledAppFlow
                    from google.auth. transport.requests import Request
                    from googleapiclient.discovery import build
                    import pickle
                except ImportError as e:
                    self.log(f"❌ Google API libraries not installed: {str(e)}")
                    self.log("💡 Install with: pip install google-api-python-client google-auth-oauthlib")
                    wx.CallAfter(messagebox.showerror, "Missing Libraries", 
                                "Google API libraries not installed.\nPlease install:\npip install google-api-python-client google-auth-oauthlib")
                    return
                
                SCOPES = ['https://www.googleapis.com/auth/youtube. force-ssl']
                
                creds = None
                token_path = self.config.get('paths', 'token_path', fallback='token_livestream.json')
                
                # Load existing credentials
                if os.path.exists(token_path):
                    with open(token_path, 'rb') as token:
                        creds = pickle.load(token)
                
                # Refresh or get new credentials
                if not creds or not creds.valid:
                    if creds and creds.expired and creds.refresh_token:
                        creds. refresh(Request())
                        self.log("✅ Credentials refreshed")
                    else: 
                        flow = InstalledAppFlow.from_client_secrets_file(client_secret, SCOPES)
                        creds = flow.run_local_server(port=0)
                        self.log("✅ New credentials obtained")
                    
                    # Save credentials
                    with open(token_path, 'wb') as token:
                        pickle.dump(creds, token)
                
                # Build YouTube service
                self.youtube = build('youtube', 'v3', credentials=creds)
                
                wx.CallAfter(self._on_auth_success)
            
            except Exception as e:
                self.log(f"❌ Authentication failed: {str(e)}")
                wx.CallAfter(messagebox.showerror, "Error", f"Authentication failed:\n{str(e)}")
        
        threading.Thread(target=authenticate, daemon=True).start()
    
    def _on_auth_success(self):
        """Handle successful authentication (called from main thread)."""
        self.authenticated = True
        self.status_btn.SetLabel("Status: Authenticated")
        self.status_btn.SetBackgroundColour(wx.Colour(40, 167, 69))
        self.create_btn.Enable()
        self.log("✅ Authentication successful")
    
    def on_create_broadcast(self, event):
        """Handle create broadcast button."""
        if not self.authenticated:
            messagebox.showerror("Error", "Please authenticate first!")
            return
        
        self.log("📡 Creating broadcast...")
        
        # Run broadcast creation in background thread
        def create_broadcast():
            try:
                # Create broadcast with user-provided metadata
                delay_minutes = self.delay_spin.GetValue()
                start_time = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)
                scheduled_start = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
                
                broadcast_response = self.youtube.liveBroadcasts().insert(
                    part="snippet,status,contentDetails",
                    body={
                        "snippet": {
                            "title":  self.title_ctrl.GetValue(),
                            "description": self.desc_ctrl.GetValue(),
                            "scheduledStartTime": scheduled_start
                        },
                        "status": {
                            "privacyStatus": self.privacy_combo.GetValue()
                        },
                        "contentDetails": {
                            "enableAutoStart": False,
                            "enableAutoStop": False
                        }
                    }
                ).execute()
                
                self.broadcast_id = broadcast_response['id']
                self.log(f"✅ Broadcast created:  {self.broadcast_id}")
                self.log(f"   Title: {self.title_ctrl.GetValue()}")
                self.log(f"   Privacy: {self.privacy_combo. GetValue()}")
                self. log(f"   Scheduled:  {scheduled_start}")
                
                # Create stream
                stream_response = self.youtube.liveStreams().insert(
                    part="snippet,cdn",
                    body={
                        "snippet": {
                            "title": "Stream from Glidly Pro"
                        },
                        "cdn": {
                            "frameRate": "variable",
                            "ingestionType": "rtmp",
                            "resolution": "variable"
                        }
                    }
                ).execute()
                
                stream_id = stream_response['id']
                stream_name = stream_response['cdn']['ingestionInfo']['streamName']
                ingestion_address = stream_response['cdn']['ingestionInfo']['ingestionAddress']
                
                # Use RTMPS (port 443) for better firewall compatibility
                if ingestion_address.startswith('rtmp://'):
                    ingestion_address_secure = ingestion_address.replace('rtmp://', 'rtmps://') + ':443'
                    self.rtmp_url = f"{ingestion_address_secure}/{stream_name}"
                    self.log("💡 Using RTMPS (port 443) for better firewall compatibility")
                else:
                    self.rtmp_url = f"{ingestion_address}/{stream_name}"
                
                self.log(f"✅ Stream created: {stream_id}")
                
                # Bind broadcast to stream
                self.youtube.liveBroadcasts().bind(
                    part="id,contentDetails",
                    id=self.broadcast_id,
                    streamId=stream_id
                ).execute()
                
                self. log("✅ Broadcast bound to stream")
                
                wx.CallAfter(self._on_broadcast_created)
            
            except Exception as e:
                self.log(f"❌ Broadcast creation failed: {str(e)}")
                wx.CallAfter(messagebox.showerror, "Error", f"Failed to create broadcast:\n{str(e)}")
        
        threading.Thread(target=create_broadcast, daemon=True).start()
    
    def _on_broadcast_created(self):
        """Handle successful broadcast creation (called from main thread)."""
        self.status_btn.SetLabel("Status: Broadcast Created")
        self.start_video_btn.Enable()
        self.test_live_btn.Enable()
        self.check_btn.Enable()
    
    def on_start_video(self, event):
        """Handle start video button."""
        video_path = self.config.get('paths', 'last_video_path', fallback='')
        if not video_path or not os.path.exists(video_path):
            messagebox. showerror("Error", "Please select a valid video file first!")
            return
        
        if not self.rtmp_url:
            messagebox.showerror("Error", "Please create a broadcast first!")
            return
        
        # Get selected settings
        resolution = self.resolution_combo.GetValue()
        fps = int(self.fps_combo.GetValue())
        loop_duration = self.loop_duration_combo.GetValue()
        
        # Resolution mapping
        resolution_map = {
            "240p": {"height": 240, "maxrate": "400k", "bufsize": "800k"},
            "360p": {"height": 360, "maxrate": "800k", "bufsize": "1600k"},
            "480p":  {"height": 480, "maxrate": "1500k", "bufsize": "3000k"},
            "720p": {"height": 720, "maxrate": "3000k", "bufsize": "6000k"},
            "1080p":  {"height": 1080, "maxrate": "6000k", "bufsize": "12000k"},
            "1440p":  {"height": 1440, "maxrate": "12000k", "bufsize": "24000k"},
            "4K": {"height": 2160, "maxrate": "25000k", "bufsize": "50000k"}
        }
        
        res_config = resolution_map.get(resolution, resolution_map["720p"])
        
        # Get video duration for loop calculation
        from core.config import config
        ffmpeg_path = config.ffmpeg_path
        
        video_duration = self.get_video_duration(video_path, ffmpeg_path)
        
        if not video_duration:
            self.log("⚠️ Could not detect video duration, using default loop settings")
            video_duration = 8.0
        else:
            self.log(f"📹 Video duration: {video_duration:. 2f} seconds")
        
        # Calculate loop count based on duration
        loop_duration_map = {
            "1 Hour": 3600,
            "2 Hours": 7200,
            "4 Hours": 14400,
            "8 Hours": 28800,
            "Forever": -1
        }
        
        target_duration = loop_duration_map.get(loop_duration, -1)
        
        if target_duration == -1:
            stream_loop_count = -1
            loop_info = "Forever (seamless loop)"
        else:
            stream_loop_count = int(target_duration / video_duration)
            loop_info = f"{loop_duration} (~{stream_loop_count} loops)"
        
        self.log(f"🎥 Starting video stream:  {os.path.basename(video_path)}")
        self.log(f"   Resolution: {resolution} ({res_config['height']}p)")
        self.log(f"   FPS:  {fps}")
        self.log(f"   Bitrate: {res_config['maxrate']}")
        self.log(f"   Loop Duration: {loop_info}")
        
        # Create temporary loop list file for concat demuxer
        self.temp_loop_file = "temp_livestream_loop.txt"
        
        # Convert to absolute path for concat safety
        video_path_abs = os.path.abspath(video_path)
        
        with open(self.temp_loop_file, 'w') as f:
            # Use forward slashes and escape for Windows paths
            video_path_escaped = video_path_abs.replace('\\', '/')
            f.write(f"file '{video_path_escaped}'\n")
        
        self.log("✅ Created loop configuration file")
        
        # FFmpeg command with seamless looping and connection timeout
        cmd = [
            ffmpeg_path,
            '-timeout', '10000000',
            '-re',
            '-f', 'concat',
            '-safe', '0',
            '-stream_loop', str(stream_loop_count),
            '-i', self.temp_loop_file,
            '-vf', f'scale=-2:{res_config["height"]},fps={fps}',
            '-c:v', 'libx264',
            '-preset', 'veryfast',
            '-maxrate', res_config['maxrate'],
            '-bufsize', res_config['bufsize'],
            '-c:a', 'aac',
            '-b:a', '128k',
            '-f', 'flv',
            self.rtmp_url
        ]
        
        try:
            self.stream_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Start thread to capture FFmpeg output for debugging
            def log_ffmpeg_output():
                """Read FFmpeg stderr and log important messages to UI."""
                while self.stream_process and self.stream_process.poll() is None:
                    try: 
                        line = self.stream_process.stderr.readline()
                        if not line:
                            break
                        
                        decoded = line.decode('utf-8', errors='ignore').strip()
                        if not decoded:
                            continue
                        
                        # Filter:  only log important messages
                        lower = decoded.lower()
                        
                        # Log errors, warnings, and connection info
                        if any(keyword in lower for keyword in [
                            'error', 'warning', 'failed', 'invalid', 'could not',
                            'connection', 'rtmp', 'stream', 'output #'
                        ]):
                            # Skip progress lines that contain those keywords
                            if not decoded.startswith('frame='):
                                self.log(f"[FFmpeg] {decoded}")
                        
                        # Also log initial stream configuration
                        elif any(keyword in lower for keyword in ['input #', 'duration:', 'encoder']):
                            self.log(f"[FFmpeg] {decoded}")
                    
                    except Exception: 
                        break
                
                # Log when FFmpeg exits
                if self.stream_process: 
                    returncode = self.stream_process. poll()
                    if returncode is not None and returncode != 0:
                        self.log(f"[FFmpeg] Process exited with code {returncode}")
            
            threading.Thread(target=log_ffmpeg_output, daemon=True).start()
            
            self.log("✅ Video stream started (seamless looping enabled)")
            self.log("⏳ Please wait 30-40 seconds for stream to stabilize")
            self.status_btn.SetLabel("Status: Streaming")
            self.status_btn.SetBackgroundColour(wx.Colour(255, 193, 7))
            self.stop_btn.Enable()
        
        except Exception as e: 
            self.log(f"❌ Failed to start stream: {str(e)}")
            messagebox.showerror("Error", f"Failed to start stream:\n{str(e)}")
            # Cleanup temp file if stream failed
            if os.path.exists(self.temp_loop_file):
                os.remove(self.temp_loop_file)
    
    def on_test_live(self, event):
        """Handle test live button - transition broadcast to testing."""
        if not self.broadcast_id:
            messagebox. showerror("Error", "No broadcast created!")
            return
        
        if not self.stream_process or self.stream_process.poll() is not None:
            messagebox.showerror("Error", "Please start video stream first!\n\nClick 'Start Video Stream' and wait for stream to stabilize.")
            return
        
        self.log("🔍 Checking stream ingestion status...")
        
        def test_live():
            try:
                # First, check if stream is receiving data
                response = self.youtube.liveBroadcasts().list(
                    part="status,contentDetails",
                    id=self.broadcast_id
                ).execute()
                
                if not response['items']:
                    self.log("❌ Broadcast not found")
                    wx.CallAfter(messagebox.showerror, "Error", "Broadcast not found!")
                    return
                
                broadcast = response['items'][0]
                stream_status = broadcast['status']. get('streamStatus', 'inactive')
                
                self.log(f"📊 Stream ingestion status: {stream_status}")
                
                # Check if stream is active
                if stream_status not in ['active', 'good']:
                    error_msg = f"Stream is not active yet!\n\nCurrent stream status: {stream_status}\n\n" \
                                f"YouTube is not receiving stream data yet.\n\n" \
                                f"Please:\n" \
                                f"1. Wait 30-40 seconds for FFmpeg to establish connection\n" \
                                f"2. Check that FFmpeg process is still running\n" \
                                f"3. Click 'Check Connection' to verify stream status\n" \
                                f"4. Try 'Test Live' again when stream status is 'active'"
                    self.log(f"❌ {error_msg}")
                    wx.CallAfter(messagebox.showwarning, "Stream Not Active", error_msg)
                    return
                
                # Stream is active, proceed with transition to testing
                self.log("✅ Stream is active, transitioning to testing mode...")
                
                self.youtube.liveBroadcasts().transition(
                    part="status",
                    id=self.broadcast_id,
                    broadcastStatus="testing"
                ).execute()
                
                self.log("✅ Broadcast is now in TESTING mode")
                self.log("⏳ Wait another 10-20 seconds for stream to fully stabilize")
                self.log("💡 Click 'Check Connection' to verify stream is stable")
                wx.CallAfter(self._on_testing)
            
            except Exception as e: 
                self.log(f"❌ Failed to start testing: {str(e)}")
                wx.CallAfter(messagebox.showerror, "Error", f"Failed to start testing:\n{str(e)}")
        
        threading.Thread(target=test_live, daemon=True).start()
    
    def _on_testing(self):
        """Handle testing status (called from main thread)."""
        self.status_btn.SetLabel("Status: Testing")
        self.status_btn.SetBackgroundColour(wx.Colour(255, 193, 7))
        self.test_live_btn. Disable()
        self.go_live_btn.Enable()
    
    def on_check_connection(self, event):
        """Handle check connection button."""
        if not self.broadcast_id:
            messagebox.showerror("Error", "No broadcast created!")
            return
        
        self.log("🔍 Checking connection status...")
        
        def check():
            try:
                response = self.youtube.liveBroadcasts().list(
                    part="status",
                    id=self.broadcast_id
                ).execute()
                
                if response['items']:
                    status = response['items'][0]['status']['lifeCycleStatus']
                    stream_status = response['items'][0]['status']. get('streamStatus', 'unknown')
                    self.log(f"📊 Broadcast lifecycle:  {status}")
                    self. log(f"📊 Stream status: {stream_status}")
                    
                    status_msg = f"Lifecycle: {status}\nStream: {stream_status}"
                    wx.CallAfter(messagebox.showinfo, "Status", status_msg)
                else: 
                    self.log("❌ Broadcast not found")
            
            except Exception as e: 
                self.log(f"❌ Failed to check status: {str(e)}")
        
        threading.Thread(target=check, daemon=True).start()
    
    def on_go_live(self, event):
        """Handle go live button."""
        if not self.broadcast_id:
            messagebox.showerror("Error", "No broadcast created!")
            return
        
        result = messagebox.askyesno(
            "Confirm",
            "Make the broadcast live?\n\n⚠️ Make sure:\n1. Video stream is running\n2. Stream has been in 'Testing' mode for 10-30 seconds\n3. 'Check Connection' shows stream is active"
        )
        if not result:
            return
        
        self.log("🔍 Checking stream status before going live...")
        
        def go_live():
            try:
                # First, check broadcast status
                response = self.youtube.liveBroadcasts().list(
                    part="status,contentDetails",
                    id=self.broadcast_id
                ).execute()
                
                if not response['items']:
                    self.log("❌ Broadcast not found")
                    wx.CallAfter(messagebox. showerror, "Error", "Broadcast not found!")
                    return
                
                broadcast = response['items'][0]
                lifecycle_status = broadcast['status']['lifeCycleStatus']
                stream_status = broadcast['status']. get('streamStatus', 'unknown')
                
                self.log(f"📊 Broadcast lifecycle: {lifecycle_status}")
                self.log(f"📊 Stream status: {stream_status}")
                
                # Check if broadcast is in testing mode
                if lifecycle_status != 'testing':
                    error_msg = f"Broadcast must be in testing mode first!\n\nCurrent status: {lifecycle_status}\n\n" \
                                f"Please:\n1. Click 'Test Live' first\n2. Wait 10-30 seconds\n3. Click 'Check Connection' to verify\n4. Try 'Go Live' again when status is 'testing'"
                    self.log(f"❌ Cannot go live:  {error_msg}")
                    wx.CallAfter(messagebox.showerror, "Not in Testing Mode", error_msg)
                    return
                
                # Check if stream is active
                if stream_status not in ['active', 'good']: 
                    error_msg = f"Stream is not ready yet!\n\nStream status: {stream_status}\n\n" \
                                f"Please:\n1. Make sure 'Start Video Stream' is running\n2. Wait 10-30 seconds for stream to stabilize\n3. Click 'Check Connection' to verify\n4. Try 'Go Live' again when stream is active"
                    self.log(f"❌ Cannot go live: {error_msg}")
                    wx.CallAfter(messagebox.showerror, "Stream Not Ready", error_msg)
                    return
                
                # Stream is ready, proceed with transition
                self.log("✅ Stream is active, transitioning to live...")
                
                self.youtube. liveBroadcasts().transition(
                    part="status",
                    id=self.broadcast_id,
                    broadcastStatus="live"
                ).execute()
                
                self.log("🔴 Broadcast is now LIVE!")
                wx.CallAfter(self._on_live)
            
            except Exception as e:
                self.log(f"❌ Failed to go live: {str(e)}")
                wx.CallAfter(messagebox.showerror, "Error", f"Failed to go live:\n{str(e)}")
        
        threading.Thread(target=go_live, daemon=True).start()
    
    def _on_live(self):
        """Handle live status (called from main thread)."""
        self.status_btn.SetLabel("Status: 🔴 LIVE")
        self.status_btn.SetBackgroundColour(wx.Colour(220, 53, 69))
        self.go_live_btn.Disable()
    
    def on_stop_stream(self, event):
        """Handle stop stream button."""
        if self.stream_process:
            self.log("⏹ Stopping stream...")
            self.stream_process.terminate()
            self.stream_process.wait()
            self.stream_process = None
            self.log("✅ Stream stopped")
            self.status_btn.SetLabel("Status: Stopped")
            self.status_btn.SetBackgroundColour(wx.SystemSettings.GetColour(wx. SYS_COLOUR_BTNFACE))
            self.stop_btn. Disable()
            self.go_live_btn. Disable()
        
        # Cleanup temporary loop file
        if self.temp_loop_file and os.path.exists(self.temp_loop_file):
            try:
                os.remove(self.temp_loop_file)
                self.log("✅ Cleaned up temporary files")
            except Exception as e: 
                self.log(f"⚠️ Could not delete temp file: {e}")
            self.temp_loop_file = None


class PlaceholderLivestreamPanel(wx.Panel):
    """Placeholder panel for livestream platforms coming soon."""
    
    def __init__(self, parent, platform_name):
        """Initialize placeholder panel. 
        
        Args:
            parent: Parent window
            platform_name: Name of the platform
        """
        super().__init__(parent)
        
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Title
        title = wx.StaticText(self, label=f"{platform_name} Livestream")
        title_font = wx.Font(12, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        title.SetFont(title_font)
        main_sizer.Add(title, 0, wx. ALL, 10)
        
        # Coming soon message
        coming_soon = wx.StaticText(self, label="🚧 Coming Soon 🚧")
        coming_soon_font = wx.Font(16, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx. FONTWEIGHT_BOLD)
        coming_soon.SetFont(coming_soon_font)
        coming_soon. SetForegroundColour(wx. Colour(255, 165, 0))
        main_sizer.Add(coming_soon, 0, wx. ALIGN_CENTER | wx.ALL, 20)
        
        info_text = wx.StaticText(self, label=f"{platform_name} livestreaming will be added in a future update.\nStay tuned!")
        info_text.SetForegroundColour(wx.Colour(128, 128, 128))
        main_sizer.Add(info_text, 0, wx.ALIGN_CENTER | wx. ALL, 10)
        
        self.SetSizer(main_sizer)