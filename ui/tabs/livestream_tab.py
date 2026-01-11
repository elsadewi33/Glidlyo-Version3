"""Livestream tab with YouTube streaming capabilities."""
import os
import configparser
import subprocess
import threading
import wx
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
        self.notebook.AddPage(self.youtube_tab, "YouTube")
        self.notebook.AddPage(self.facebook_tab, "Facebook")
        self.notebook.AddPage(self.tiktok_tab, "TikTok")
        self.notebook.AddPage(self.instagram_tab, "Instagram")
        
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
        
        # Build UI
        self._build_ui()
    
    def _build_ui(self):
        """Build the UI components."""
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Title
        title = wx.StaticText(self, label="YouTube Livestream")
        title_font = wx.Font(12, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        title.SetFont(title_font)
        main_sizer.Add(title, 0, wx.ALL, 10)
        
        # Configuration section
        config_box = wx.StaticBox(self, label="Configuration")
        config_sizer = wx.StaticBoxSizer(config_box, wx.VERTICAL)
        
        grid = wx.FlexGridSizer(rows=3, cols=3, vgap=5, hgap=10)
        
        # Client secret file
        grid.Add(wx.StaticText(config_box, label="Client Secret:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.client_secret_label = wx.StaticText(config_box, label=os.path.basename(self.config.get('paths', 'client_secret_path', fallback='Not set')))
        self.client_secret_label.SetForegroundColour(wx.Colour(0, 0, 255))
        grid.Add(self.client_secret_label, 1, wx.EXPAND)
        btn_client_secret = wx.Button(config_box, label="Browse...")
        btn_client_secret.Bind(wx.EVT_BUTTON, self.on_browse_client_secret)
        grid.Add(btn_client_secret, 0)
        
        # Token path
        grid.Add(wx.StaticText(config_box, label="Token Path:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.token_label = wx.StaticText(config_box, label=self.config.get('paths', 'token_path', fallback='token_livestream.json'))
        self.token_label.SetForegroundColour(wx.Colour(0, 0, 255))
        grid.Add(self.token_label, 1, wx.EXPAND)
        grid.AddSpacer(0)
        
        # Video file
        grid.Add(wx.StaticText(config_box, label="Video File:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.video_label = wx.StaticText(config_box, label=os.path.basename(self.config.get('paths', 'last_video_path', fallback='Not set')))
        self.video_label.SetForegroundColour(wx.Colour(0, 0, 255))
        grid.Add(self.video_label, 1, wx.EXPAND)
        btn_video = wx.Button(config_box, label="Browse...")
        btn_video.Bind(wx.EVT_BUTTON, self.on_browse_video)
        grid.Add(btn_video, 0)
        
        grid.AddGrowableCol(1, 1)
        config_sizer.Add(grid, 0, wx.EXPAND | wx.ALL, 5)
        
        main_sizer.Add(config_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        # Control buttons
        control_panel = wx.Panel(self)
        control_sizer = wx.GridSizer(rows=3, cols=3, vgap=5, hgap=5)
        
        # Row 1: Auth, Create, Start
        self.auth_btn = wx.Button(control_panel, label="Authenticate")
        self.auth_btn.Bind(wx.EVT_BUTTON, self.on_authenticate)
        control_sizer.Add(self.auth_btn, 0, wx.EXPAND)
        
        self.create_btn = wx.Button(control_panel, label="Create Broadcast")
        self.create_btn.Disable()
        self.create_btn.Bind(wx.EVT_BUTTON, self.on_create_broadcast)
        control_sizer.Add(self.create_btn, 0, wx.EXPAND)
        
        self.start_video_btn = wx.Button(control_panel, label="Start Video (240p)")
        self.start_video_btn.Disable()
        self.start_video_btn.Bind(wx.EVT_BUTTON, self.on_start_video)
        control_sizer.Add(self.start_video_btn, 0, wx.EXPAND)
        
        # Row 2: Check, Go Live, Stop
        self.check_btn = wx.Button(control_panel, label="Check Connection")
        self.check_btn.Disable()
        self.check_btn.Bind(wx.EVT_BUTTON, self.on_check_connection)
        control_sizer.Add(self.check_btn, 0, wx.EXPAND)
        
        self.go_live_btn = wx.Button(control_panel, label="Go Live")
        self.go_live_btn.Disable()
        self.go_live_btn.SetBackgroundColour(wx.Colour(220, 53, 69))
        self.go_live_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        self.go_live_btn.Bind(wx.EVT_BUTTON, self.on_go_live)
        control_sizer.Add(self.go_live_btn, 0, wx.EXPAND)
        
        self.stop_btn = wx.Button(control_panel, label="Stop Stream")
        self.stop_btn.Disable()
        self.stop_btn.Bind(wx.EVT_BUTTON, self.on_stop_stream)
        control_sizer.Add(self.stop_btn, 0, wx.EXPAND)
        
        # Row 3: Status button spans all columns
        self.status_btn = wx.Button(control_panel, label="Status: Not Authenticated")
        self.status_btn.Disable()
        control_sizer.Add(self.status_btn, 0, wx.EXPAND)
        control_sizer.AddSpacer(0)
        control_sizer.AddSpacer(0)
        
        control_panel.SetSizer(control_sizer)
        main_sizer.Add(control_panel, 0, wx.EXPAND | wx.ALL, 5)
        
        # Log area
        log_label = wx.StaticText(self, label="Activity Log:")
        main_sizer.Add(log_label, 0, wx.TOP | wx.LEFT, 10)
        
        self.log_text = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.log_text.SetBackgroundColour(wx.Colour(30, 30, 30))
        self.log_text.SetForegroundColour(wx.Colour(0, 255, 0))
        self.log_text.SetFont(wx.Font(9, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        main_sizer.Add(self.log_text, 1, wx.EXPAND | wx.ALL, 5)
        
        self.SetSizer(main_sizer)
    
    def load_config(self):
        """Load configuration from config file."""
        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
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
            filetypes=(("Video files", "*.mp4;*.avi;*.mov;*.mkv"), ("All files", "*.*"))
        )
        if path:
            self.config['paths']['last_video_path'] = path
            self.video_label.SetLabel(os.path.basename(path))
            self.save_config()
    
    def on_authenticate(self, event):
        """Handle authenticate button."""
        client_secret = self.config.get('paths', 'client_secret_path', fallback='')
        if not client_secret or not os.path.exists(client_secret):
            messagebox.showerror("Error", "Please select a valid client secret file first!")
            return
        
        self.log("🔐 Authenticating with YouTube...")
        
        # Run authentication in background thread
        def authenticate():
            try:
                # Lazy import Google API libraries to avoid import errors when not used
                # If libraries not installed, provide clear error message
                try:
                    from google.oauth2.credentials import Credentials
                    from google_auth_oauthlib.flow import InstalledAppFlow
                    from google.auth.transport.requests import Request
                    from googleapiclient.discovery import build
                    import pickle
                except ImportError as e:
                    self.log(f"❌ Google API libraries not installed: {str(e)}")
                    self.log("💡 Install with: pip install google-api-python-client google-auth-oauthlib")
                    wx.CallAfter(messagebox.showerror, "Missing Libraries", 
                                "Google API libraries not installed.\nPlease install:\npip install google-api-python-client google-auth-oauthlib")
                    return
                
                SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']
                
                creds = None
                token_path = self.config.get('paths', 'token_path', fallback='token_livestream.json')
                
                # Load existing credentials
                if os.path.exists(token_path):
                    with open(token_path, 'rb') as token:
                        creds = pickle.load(token)
                
                # Refresh or get new credentials
                if not creds or not creds.valid:
                    if creds and creds.expired and creds.refresh_token:
                        creds.refresh(Request())
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
                # Create broadcast
                broadcast_response = self.youtube.liveBroadcasts().insert(
                    part="snippet,status,contentDetails",
                    body={
                        "snippet": {
                            "title": "Livestream from Glidly Pro",
                            "scheduledStartTime": "2030-01-01T00:00:00.000Z"
                        },
                        "status": {
                            "privacyStatus": "unlisted"
                        },
                        "contentDetails": {
                            "enableAutoStart": False,
                            "enableAutoStop": False
                        }
                    }
                ).execute()
                
                self.broadcast_id = broadcast_response['id']
                self.log(f"✅ Broadcast created: {self.broadcast_id}")
                
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
                
                self.rtmp_url = f"{ingestion_address}/{stream_name}"
                self.log(f"✅ Stream created: {stream_id}")
                
                # Bind broadcast to stream
                self.youtube.liveBroadcasts().bind(
                    part="id,contentDetails",
                    id=self.broadcast_id,
                    streamId=stream_id
                ).execute()
                
                self.log("✅ Broadcast bound to stream")
                
                wx.CallAfter(self._on_broadcast_created)
            
            except Exception as e:
                self.log(f"❌ Broadcast creation failed: {str(e)}")
                wx.CallAfter(messagebox.showerror, "Error", f"Failed to create broadcast:\n{str(e)}")
        
        threading.Thread(target=create_broadcast, daemon=True).start()
    
    def _on_broadcast_created(self):
        """Handle successful broadcast creation (called from main thread)."""
        self.status_btn.SetLabel("Status: Broadcast Created")
        self.start_video_btn.Enable()
        self.check_btn.Enable()
    
    def on_start_video(self, event):
        """Handle start video button."""
        video_path = self.config.get('paths', 'last_video_path', fallback='')
        if not video_path or not os.path.exists(video_path):
            messagebox.showerror("Error", "Please select a valid video file first!")
            return
        
        if not self.rtmp_url:
            messagebox.showerror("Error", "Please create a broadcast first!")
            return
        
        self.log(f"🎥 Starting video stream (240p): {os.path.basename(video_path)}")
        
        # Start FFmpeg stream
        from core.config import config
        ffmpeg_path = config.ffmpeg_path
        
        # FFmpeg command for 240p streaming
        cmd = [
            ffmpeg_path,
            '-re',  # Read input at native frame rate
            '-i', video_path,
            '-vf', 'scale=-2:240',  # Scale to 240p
            '-c:v', 'libx264',
            '-preset', 'veryfast',
            '-maxrate', '400k',
            '-bufsize', '800k',
            '-c:a', 'aac',
            '-b:a', '64k',
            '-f', 'flv',
            self.rtmp_url
        ]
        
        try:
            self.stream_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.log("✅ Video stream started")
            self.status_btn.SetLabel("Status: Streaming")
            self.status_btn.SetBackgroundColour(wx.Colour(255, 193, 7))
            self.stop_btn.Enable()
            self.go_live_btn.Enable()
        
        except Exception as e:
            self.log(f"❌ Failed to start stream: {str(e)}")
            messagebox.showerror("Error", f"Failed to start stream:\n{str(e)}")
    
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
                    self.log(f"📊 Broadcast status: {status}")
                    wx.CallAfter(messagebox.showinfo, "Status", f"Broadcast status: {status}")
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
        
        result = messagebox.askyesno("Confirm", "Make the broadcast live?")
        if not result:
            return
        
        self.log("🔴 Going live...")
        
        def go_live():
            try:
                self.youtube.liveBroadcasts().transition(
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
        self.status_btn.SetLabel("Status: LIVE")
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
            self.status_btn.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE))
            self.stop_btn.Disable()
            self.go_live_btn.Disable()


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
        main_sizer.Add(title, 0, wx.ALL, 10)
        
        # Coming soon message
        coming_soon = wx.StaticText(self, label="🚧 Coming Soon 🚧")
        coming_soon_font = wx.Font(16, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        coming_soon.SetFont(coming_soon_font)
        coming_soon.SetForegroundColour(wx.Colour(255, 165, 0))
        main_sizer.Add(coming_soon, 0, wx.ALIGN_CENTER | wx.ALL, 20)
        
        info_text = wx.StaticText(self, label=f"{platform_name} livestreaming will be added in a future update.\nStay tuned!")
        info_text.SetForegroundColour(wx.Colour(128, 128, 128))
        main_sizer.Add(info_text, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        
        self.SetSizer(main_sizer)
