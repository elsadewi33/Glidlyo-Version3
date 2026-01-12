"""Main window UI for Glidly Pro AI Automator with tabbed interface."""
import os
import json
import threading
import wx
from ui.variables import SimpleVar
from ui.dialogs import messagebox
from core.config import config
from core.models import GenerationConfig
from core.logger import Logger
from services.pipeline import Pipeline
from ui.tabs import VideoGeneratorTab, VideoProcessorTab, VideoUploaderTab, LivestreamTab


class MainWindow(wx.Frame):
    """Main application window with tabbed interface."""
    
    def __init__(self, parent=None, title="Glidly Pro - AI Automator (Tabbed UI)"):
        """Initialize main window. 
        
        Args:
            parent: Parent window
            title:  Window title
        """
        super().__init__(parent, title=title, size=(1000, 800))
        self.SetMinSize(wx.Size(900, 700))
        
        # Initialize variables
        self.prompt_folder = SimpleVar("")
        self.mode = SimpleVar("Shorts")
        self.generator = SimpleVar("Veo 3.1")
        self.timeout = SimpleVar(180)
        self.auto_merge_var = SimpleVar(True)
        self.upscale_var = SimpleVar(False)
        self.upload_youtube_var = SimpleVar(False)
        self.loop_duration = SimpleVar(60)
        self.gen_method = SimpleVar("Default")
        self.seed_image_path = SimpleVar("")
        self.flow_account_start = SimpleVar(config.flow_account_start)
        self.google_flow_username = SimpleVar("")
        self.google_flow_password = SimpleVar("")
        self.video_gen_subcategory = SimpleVar("Default")
        
        # YouTube channel mapping
        self.youtube_channels = {
            "Shorts": {"name": "", "credentials": ""},
            "Sound Relief": {"name": "", "credentials":  ""},
            "Restorasi": {"name": "", "credentials": ""},
            "Home Renovation": {"name": "", "credentials":  ""}
        }
        
        # Control state with threading. Event for better stop/pause handling
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.is_paused = False
        self.is_running = False
        self.pipeline_thread = None  # Track pipeline thread for cleanup
        
        # UI refs
        self.log_widget = None
        self.log_label = None
        self. ctrl_panel = None
        
        # Build UI
        self.setup_ui()
        
        # Load channels
        self.load_youtube_channels()
    
    def setup_ui(self):
        """Setup the user interface with tabbed layout."""
        # Main panel
        main_panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Title
        title = wx.StaticText(main_panel, label="GLIDLY AI AUTOMATOR")
        title_font = wx.Font(16, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        title.SetFont(title_font)
        main_sizer.Add(title, 0, wx. TOP | wx.BOTTOM | wx.ALIGN_CENTER_HORIZONTAL, 10)
        
        # Create app_state dictionary to share with tabs
        self.app_state = {
            'prompt_folder': self.prompt_folder,
            'mode': self.mode,
            'generator': self. generator,
            'timeout': self.timeout,
            'auto_merge_var': self.auto_merge_var,
            'upscale_var': self.upscale_var,
            'upload_youtube_var': self.upload_youtube_var,
            'loop_duration': self.loop_duration,
            'gen_method':  self.gen_method,
            'seed_image_path': self.seed_image_path,
            'flow_account_start':  self.flow_account_start,
            'google_flow_username': self.google_flow_username,
            'google_flow_password': self.google_flow_password,
            'video_gen_subcategory': self.video_gen_subcategory,
            'youtube_channels': self.youtube_channels,
            'log_callback': self.log,
        }
        
        # Create main notebook for top-level tabs
        self.notebook = wx.Notebook(main_panel)
        
        # Create tabs
        self.video_gen_tab = VideoGeneratorTab(self.notebook, self.app_state)
        self.video_proc_tab = VideoProcessorTab(self.notebook, self.app_state)
        self.video_upload_tab = VideoUploaderTab(self.notebook, self.app_state)
        self.livestream_tab = LivestreamTab(self.notebook, self.app_state)
        
        # Add tabs to notebook
        self. notebook.AddPage(self.video_gen_tab, "Video Generator")
        self.notebook.AddPage(self.video_proc_tab, "Video Processor")
        self.notebook.AddPage(self.video_upload_tab, "Video Uploader")
        self.notebook.AddPage(self.livestream_tab, "Livestream")
        
        # Bind main notebook tab change to show/hide control buttons
        self.notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self._on_main_tab_changed)
        
        main_sizer.Add(self. notebook, 1, wx. EXPAND | wx.ALL, 5)
        
        # Activity Log
        self.log_label = wx.StaticText(main_panel, label="Video Generation Log:")
        main_sizer.Add(self.log_label, 0, wx.TOP | wx.LEFT, 10)
        
        self.log_widget = wx.TextCtrl(main_panel, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(-1, 150))
        self.log_widget.SetBackgroundColour(wx. Colour(30, 30, 30))
        self.log_widget.SetForegroundColour(wx. Colour(0, 255, 0))
        self.log_widget.SetFont(wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        main_sizer. Add(self.log_widget, 0, wx.EXPAND | wx. ALL, 5)
        
        # Control Buttons
        self._setup_control_buttons(main_panel, main_sizer)
        
        main_panel.SetSizer(main_sizer)
    
    def _setup_control_buttons(self, parent, sizer):
        """Setup control buttons section."""
        self.ctrl_panel = wx.Panel(parent)
        ctrl_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.start_btn = wx.Button(self.ctrl_panel, label="▶ START")
        self.start_btn.SetBackgroundColour(wx. Colour(40, 167, 69))
        self.start_btn.SetForegroundColour(wx. Colour(255, 255, 255))
        self.start_btn.SetFont(wx.Font(10, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.start_btn.Bind(wx.EVT_BUTTON, lambda e: self. start_automation_thread())
        ctrl_sizer.Add(self.start_btn, 1, wx. EXPAND | wx.RIGHT, 5)
        
        self.pause_btn = wx.Button(self.ctrl_panel, label="⏸ PAUSE")
        self.pause_btn.SetBackgroundColour(wx.Colour(255, 193, 7))
        self.pause_btn.SetForegroundColour(wx.Colour(0, 0, 0))
        self.pause_btn.SetFont(wx.Font(10, wx. FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.pause_btn.Disable()
        self.pause_btn.Bind(wx.EVT_BUTTON, lambda e: self.toggle_pause())
        ctrl_sizer.Add(self.pause_btn, 1, wx. EXPAND | wx.RIGHT, 5)
        
        self.stop_btn = wx.Button(self.ctrl_panel, label="⏹ STOP")
        self.stop_btn.SetBackgroundColour(wx.Colour(220, 53, 69))
        self.stop_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        self.stop_btn.SetFont(wx.Font(10, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.stop_btn.Disable()
        self.stop_btn. Bind(wx.EVT_BUTTON, lambda e: self. stop_automation())
        ctrl_sizer.Add(self.stop_btn, 1, wx.EXPAND)
        
        self.ctrl_panel.SetSizer(ctrl_sizer)
        sizer.Add(self.ctrl_panel, 0, wx. EXPAND | wx.ALL, 10)
    
    # Event handlers
    def toggle_pause(self):
        """Toggle pause/resume."""
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.pause_event.clear()
            self.pause_btn.SetLabel("▶ RESUME")
            self.pause_btn.SetBackgroundColour(wx. Colour(40, 167, 69))
            self.pause_btn.SetForegroundColour(wx. Colour(255, 255, 255))
            self.log("⏸ PAUSED - Click RESUME to continue")
        else:
            self.pause_event. set()
            self.pause_btn.SetLabel("⏸ PAUSE")
            self.pause_btn.SetBackgroundColour(wx.Colour(255, 193, 7))
            self.pause_btn.SetForegroundColour(wx. Colour(0, 0, 0))
            self.log("▶ RESUMED")
    
    def stop_automation(self):
        """Stop automation - waits for cleanup before re-enabling START."""
        self.is_paused = False
        self.is_running = False
        self. stop_event.set()  # Signal stop to any running threads
        self.log("⏹ STOP - Stopping...  please wait for cleanup")
        
        # Disable all buttons immediately (will be re-enabled after cleanup)
        self.start_btn.Disable()
        self.pause_btn.Disable()
        self.stop_btn. Disable()
        
        # Start a background thread to wait for pipeline cleanup (non-blocking UI)
        def wait_for_cleanup():
            if self.pipeline_thread and self. pipeline_thread.is_alive():
                self.pipeline_thread. join(timeout=30)  # Wait max 30s
            wx.CallAfter(self._reset_ui_state)
            wx.CallAfter(self.log, "✅ Cleanup complete - ready to start again")
        
        threading.Thread(target=wait_for_cleanup, daemon=True).start()
    
    def _reset_ui_state(self):
        """Reset UI to initial state after stop."""
        self.start_btn.Enable()
        self.pause_btn.Disable()
        self.pause_btn.SetLabel("⏸ PAUSE")
        self.pause_btn.SetBackgroundColour(wx.Colour(255, 193, 7))
        self.pause_btn.SetForegroundColour(wx. Colour(0, 0, 0))
        self.stop_btn.Disable()
    
    def log(self, msg):
        """Log a message to the activity log. 
        
        Args:
            msg: Message to log
        """
        import time
        timestamp = time.strftime('%H:%M:%S')
        full_msg = f"[{timestamp}] {msg}\n"
        
        if self.log_widget:
            # Use wx.CallAfter for thread-safe UI updates
            wx.CallAfter(self._append_log, full_msg)
        else:
            print(full_msg)
    
    def _append_log(self, msg):
        """Append message to log widget (must be called from main thread).
        
        Args:
            msg: Message to append
        """
        self.log_widget.AppendText(msg)
    
    # YouTube channel management
    def load_youtube_channels(self):
        """Load YouTube channel configuration."""
        config_file = "youtube_channels.json"
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    saved_channels = json.load(f)
                self.youtube_channels. update(saved_channels)
                self.log("✅ YouTube channel settings loaded")
            except Exception as e: 
                self.log(f"⚠️ Could not load channel settings: {e}")
    
    def start_automation_thread(self):
        """Start automation in a background thread."""
        # Validation
        if not self.prompt_folder.get():
            messagebox.showwarning("Warning", "Please select JSON prompt folder first!")
            return
        
        if not config.download_path:
            messagebox.showwarning("Warning", "DOWNLOAD_PATH not found in . env file!")
            return
        
        if self.is_running:
            messagebox.showinfo("Info", "Automation already running!")
            return
        
        # Additional validations... 
        current_mode = self.mode.get()
        
        if current_mode == "Restorasi":
            intro_path = os.path.join(config.assets_folder, "intro.mp4")
            if not os. path.exists(intro_path):
                response = messagebox.askyesno(
                    "Warning",
                    "intro.mp4 not found in Assets folder.\nContinue without intro?"
                )
                if not response:
                    return
        
        if current_mode == "Sound Relief":
            music_folder = config.music_folder or os.path.join(config. assets_folder, "music")
            if not os.path.exists(music_folder):
                messagebox.showwarning(
                    "Warning",
                    f"Music folder not found:  {music_folder}\nSound Relief requires MP3 files!"
                )
                return
        
        # Validate Google Flow credentials if using Google Flow
        if self.video_gen_subcategory.get() == "Google Flow":
            if not self.google_flow_username.get() or not self.google_flow_password.get():
                messagebox.showwarning(
                    "Warning",
                    "Google Flow credentials are required!\nPlease set username and password in the Google Flow tab."
                )
                return
        
        # Log start
        self.log("=" * 50)
        self.log("🚀 STARTING AUTOMATION...")
        self.log(f"📂 Prompt Folder: {self.prompt_folder.get()}")
        self.log(f"🎯 Mode: {current_mode}")
        self.log(f"🎬 Generator: {self.generator. get()}")
        self.log(f"⏱️ Timeout: {self. timeout.get()}s")
        self.log(f"🧭 Subcategory: {self.video_gen_subcategory.get()}")
        if current_mode == "Sound Relief":
            self.log(f"🎵 Loop Duration: {self.loop_duration.get()} minutes")
        self.log("=" * 50)
        
        # Reset events
        self.stop_event. clear()
        self.pause_event.set()  # Not paused initially
        
        # Update UI state
        self.is_running = True
        self. start_btn.Disable()
        self.pause_btn.Enable()
        self.stop_btn.Enable()
        
        # Create configuration
        gen_config = GenerationConfig(
            prompt_folder=self.prompt_folder.get(),
            mode=current_mode,
            generator=self.generator.get(),
            timeout=self.timeout.get(),
            gen_method=self.gen_method.get(),
            seed_image_path=self.seed_image_path.get() if self.seed_image_path.get() else None,
            subcategory=self.video_gen_subcategory.get(),
            video_gen_subcategory=self.video_gen_subcategory.get(),  # Ensure both fields set
            google_flow_username=self.google_flow_username.get() if self.google_flow_username. get() else None,
            google_flow_password=self.google_flow_password.get() if self.google_flow_password. get() else None,
            auto_merge=self.auto_merge_var. get(),
            upscale=self.upscale_var. get(),
            upload_youtube=self.upload_youtube_var. get(),
            loop_duration=self.loop_duration.get(),
            youtube_channels=self.youtube_channels
        )
        
        # Create logger with UI callback
        logger = Logger(log_callback=self.log)
        
        # Create pipeline
        pipeline = Pipeline(config, gen_config, logger, 
                           stop_event=self.stop_event, 
                           pause_event=self.pause_event)
        
        # Run in thread
        def run_pipeline():
            try:
                pipeline.run()
                self.log("🎉 AUTOMATION COMPLETED!")
            except Exception as e:
                self.log(f"❌ Automation failed: {str(e)}")
                messagebox.showerror("Error", f"Automation failed:\n{str(e)}")
            finally:
                wx.CallAfter(self._on_automation_complete)
        
        self.pipeline_thread = threading.Thread(target=run_pipeline, daemon=True)
        self.pipeline_thread.start()
    
    def _on_automation_complete(self):
        """Handle automation completion (called from main thread)."""
        self.is_running = False
        self.start_btn.Enable()
        self.pause_btn.Disable()
        self.pause_btn.SetLabel("⏸ PAUSE")
        self.pause_btn.SetBackgroundColour(wx.Colour(255, 193, 7))
        self.pause_btn. SetForegroundColour(wx.Colour(0, 0, 0))
        self.stop_btn.Disable()
    
    def _on_main_tab_changed(self, event):
        """Handle main tab change - hide control buttons and log only for Livestream tab."""
        page_idx = event.GetSelection()
        
        # Hide control buttons and main log only for Livestream tab (index 3)
        # Video Generator (0), Video Processor (1), Video Uploader (2) all need START/STOP
        if page_idx == 3:  # Livestream tab
            # Hide control buttons and main log (Livestream has its own controls and log)
            if not self.is_running:  # Don't hide if automation is running
                self.ctrl_panel. Hide()
                self.log_label.Hide()
                self.log_widget.Hide()
        else:
            # Show control buttons and main log for all other tabs
            self.ctrl_panel.Show()
            self.log_label.Show()
            self.log_widget.Show()
        
        self.Layout()
        event.Skip()