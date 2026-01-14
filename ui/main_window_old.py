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
            title: Window title
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
            "Sound Relief": {"name": "", "credentials": ""},
            "Restorasi": {"name": "", "credentials": ""},
            "Home Renovation": {"name": "", "credentials": ""}
        }
        
        # Control state with threading.Event for better stop/pause handling
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.is_paused = False
        self.is_running = False
        
        # UI refs
        self.log_widget = None
        
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
        main_sizer.Add(title, 0, wx.TOP | wx.BOTTOM | wx.ALIGN_CENTER_HORIZONTAL, 10)
        
        # Create app_state dictionary to share with tabs
        self.app_state = {
            'prompt_folder': self.prompt_folder,
            'mode': self.mode,
            'generator': self.generator,
            'timeout': self.timeout,
            'auto_merge_var': self.auto_merge_var,
            'upscale_var': self.upscale_var,
            'upload_youtube_var': self.upload_youtube_var,
            'loop_duration': self.loop_duration,
            'gen_method': self.gen_method,
            'seed_image_path': self.seed_image_path,
            'flow_account_start': self.flow_account_start,
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
        self.notebook.AddPage(self.video_gen_tab, "Video Generator")
        self.notebook.AddPage(self.video_proc_tab, "Video Processor")
        self.notebook.AddPage(self.video_upload_tab, "Video Uploader")
        self.notebook.AddPage(self.livestream_tab, "Livestream")
        
        main_sizer.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 5)
        
        # Activity Log
        log_label = wx.StaticText(main_panel, label="Activity Log:")
        main_sizer.Add(log_label, 0, wx.TOP | wx.LEFT, 10)
        
        self.log_widget = wx.TextCtrl(main_panel, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(-1, 150))
        self.log_widget.SetBackgroundColour(wx.Colour(30, 30, 30))
        self.log_widget.SetForegroundColour(wx.Colour(0, 255, 0))
        self.log_widget.SetFont(wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        main_sizer.Add(self.log_widget, 0, wx.EXPAND | wx.ALL, 5)
        
        # Control Buttons
        self._setup_control_buttons(main_panel, main_sizer)
        
        main_panel.SetSizer(main_sizer)
    
    def _setup_control_buttons(self, parent, sizer):
        """Setup control buttons section."""
        ctrl_panel = wx.Panel(parent)
        ctrl_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.start_btn = wx.Button(ctrl_panel, label="▶ START")
        self.start_btn.SetBackgroundColour(wx.Colour(40, 167, 69))
        self.start_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        self.start_btn.SetFont(wx.Font(10, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.start_btn.Bind(wx.EVT_BUTTON, lambda e: self.start_automation_thread())
        ctrl_sizer.Add(self.start_btn, 1, wx.EXPAND | wx.RIGHT, 5)
        
        self.pause_btn = wx.Button(ctrl_panel, label="⏸ PAUSE")
        self.pause_btn.SetBackgroundColour(wx.Colour(255, 193, 7))
        self.pause_btn.SetForegroundColour(wx.Colour(0, 0, 0))
        self.pause_btn.SetFont(wx.Font(10, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.pause_btn.Disable()
        self.pause_btn.Bind(wx.EVT_BUTTON, lambda e: self.toggle_pause())
        ctrl_sizer.Add(self.pause_btn, 1, wx.EXPAND | wx.RIGHT, 5)
        
        self.stop_btn = wx.Button(ctrl_panel, label="⏹ STOP")
        self.stop_btn.SetBackgroundColour(wx.Colour(220, 53, 69))
        self.stop_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        self.stop_btn.SetFont(wx.Font(10, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.stop_btn.Disable()
        self.stop_btn.Bind(wx.EVT_BUTTON, lambda e: self.stop_automation())
        ctrl_sizer.Add(self.stop_btn, 1, wx.EXPAND)
        
        ctrl_panel.SetSizer(ctrl_sizer)
        sizer.Add(ctrl_panel, 0, wx.EXPAND | wx.ALL, 10)
    
    def _setup_path_settings(self):
        """Setup path settings section."""
        path_box = wx.StaticBox(self.scrollable_panel, label="Path Settings")
        path_sizer = wx.StaticBoxSizer(path_box, wx.VERTICAL)
        
        btn_select_prompt = wx.Button(path_box, label="Pilih Folder JSON Prompt")
        btn_select_prompt.Bind(wx.EVT_BUTTON, lambda e: self.select_prompt())
        path_sizer.Add(btn_select_prompt, 0, wx.EXPAND | wx.ALL, 5)
        
        self.prompt_folder_label = wx.StaticText(path_box, label="", style=wx.ST_NO_AUTORESIZE)
        self.prompt_folder_label.SetForegroundColour(wx.Colour(0, 0, 255))
        self.prompt_folder_label.Wrap(550)
        path_sizer.Add(self.prompt_folder_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        
        self.main_sizer.Add(path_sizer, 0, wx.EXPAND | wx.ALL, 5)
    
    def _setup_mode_selection(self):
        """Setup mode selection section."""
        mode_box = wx.StaticBox(self.scrollable_panel, label="Mode Selection")
        mode_sizer = wx.StaticBoxSizer(mode_box, wx.HORIZONTAL)
        
        modes = ["Shorts", "Sound Relief", "Restorasi", "Home Renovation"]
        lbl_mode = wx.StaticText(mode_box, label="Select Mode:")
        self.mode_combo = wx.ComboBox(mode_box, choices=modes, style=wx.CB_READONLY, size=(200, -1))
        self.mode_combo.SetValue(self.mode.get())
        self.mode_combo.Bind(wx.EVT_COMBOBOX, lambda e: self.select_mode(self.mode_combo.GetValue()))
        
        mode_sizer.Add(lbl_mode, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        mode_sizer.Add(self.mode_combo, 1, wx.ALL | wx.EXPAND, 5)
        
        self.main_sizer.Add(mode_sizer, 0, wx.EXPAND | wx.ALL, 5)
    
    def _setup_sound_relief_options(self):
        """Setup Sound Relief options section."""
        self.sound_relief_box = wx.StaticBox(self.scrollable_panel, label="Sound Relief Options")
        sound_relief_sizer = wx.StaticBoxSizer(self.sound_relief_box, wx.HORIZONTAL)
        
        lbl_loop = wx.StaticText(self.sound_relief_box, label="Loop Duration (minutes):")
        self.loop_duration_ctrl = wx.SpinCtrl(self.sound_relief_box, min=1, max=10000, initial=self.loop_duration.get())
        self.loop_duration_ctrl.Bind(wx.EVT_SPINCTRL, lambda e: self.loop_duration.set(self.loop_duration_ctrl.GetValue()))
        
        sound_relief_sizer.Add(lbl_loop, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        sound_relief_sizer.Add(self.loop_duration_ctrl, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        sound_relief_sizer.Show(False)
        
        self.main_sizer.Add(sound_relief_sizer, 0, wx.EXPAND | wx.ALL, 5)
        self.sound_relief_sizer = sound_relief_sizer
    
    def _setup_subcategory_selection(self):
        """Setup video generator subcategory selection."""
        subcategory_box = wx.StaticBox(self.scrollable_panel, label="Video Generator Type")
        subcategory_sizer = wx.StaticBoxSizer(subcategory_box, wx.HORIZONTAL)
        
        subcategories = ["Default", "Flow Video Generator", "Google Flow"]
        lbl_subcat = wx.StaticText(subcategory_box, label="Select Type:")
        self.subcategory_combo = wx.ComboBox(subcategory_box, choices=subcategories, style=wx.CB_READONLY, size=(200, -1))
        self.subcategory_combo.SetValue(self.video_gen_subcategory.get())
        self.subcategory_combo.Bind(wx.EVT_COMBOBOX, lambda e: self.select_subcategory(self.subcategory_combo.GetValue()))
        
        subcategory_sizer.Add(lbl_subcat, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        subcategory_sizer.Add(self.subcategory_combo, 1, wx.ALL | wx.EXPAND, 5)
        
        self.main_sizer.Add(subcategory_sizer, 0, wx.EXPAND | wx.ALL, 5)
    
    def _setup_configurations(self):
        """Setup configurations section."""
        config_box = wx.StaticBox(self.scrollable_panel, label="Configurations")
        config_sizer = wx.StaticBoxSizer(config_box, wx.VERTICAL)
        
        grid_cfg = wx.FlexGridSizer(rows=8, cols=2, vgap=5, hgap=10)
        
        # Generator
        grid_cfg.Add(wx.StaticText(config_box, label="Generator:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.generator_combo = wx.ComboBox(config_box, choices=["Veo 3.1", "Nexa Gen", "Sora 2"], style=wx.CB_READONLY)
        self.generator_combo.SetValue(self.generator.get())
        self.generator_combo.Bind(wx.EVT_COMBOBOX, lambda e: self.generator.set(self.generator_combo.GetValue()))
        grid_cfg.Add(self.generator_combo, 1, wx.EXPAND)
        
        # Timeout
        grid_cfg.Add(wx.StaticText(config_box, label="Timeout (sec):"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.timeout_spin = wx.SpinCtrl(config_box, min=10, max=36000, initial=self.timeout.get())
        self.timeout_spin.Bind(wx.EVT_SPINCTRL, lambda e: self.timeout.set(self.timeout_spin.GetValue()))
        grid_cfg.Add(self.timeout_spin, 1, wx.EXPAND)
        
        # Auto Merge
        self.auto_merge_cb = wx.CheckBox(config_box, label="Auto Merge Video")
        self.auto_merge_cb.SetValue(self.auto_merge_var.get())
        self.auto_merge_cb.Bind(wx.EVT_CHECKBOX, lambda e: self.auto_merge_var.set(self.auto_merge_cb.GetValue()))
        grid_cfg.Add(self.auto_merge_cb, 0, wx.ALIGN_LEFT)
        grid_cfg.AddSpacer(0)
        
        # Upscale
        self.upscale_cb = wx.CheckBox(config_box, label="Upscale to 4K")
        self.upscale_cb.SetValue(self.upscale_var.get())
        self.upscale_cb.Bind(wx.EVT_CHECKBOX, lambda e: self.upscale_var.set(self.upscale_cb.GetValue()))
        grid_cfg.Add(self.upscale_cb, 0, wx.ALIGN_LEFT)
        grid_cfg.AddSpacer(0)
        
        # Generation Method (shown only for Default subcategory)
        self.gen_method_label = wx.StaticText(config_box, label="Generation Method:")
        grid_cfg.Add(self.gen_method_label, 0, wx.ALIGN_CENTER_VERTICAL)
        self.gen_method_combo = wx.ComboBox(config_box, choices=["Default", "Flow"], style=wx.CB_READONLY)
        self.gen_method_combo.SetValue(self.gen_method.get())
        self.gen_method_combo.Bind(wx.EVT_COMBOBOX, lambda e: self.gen_method.set(self.gen_method_combo.GetValue()))
        grid_cfg.Add(self.gen_method_combo, 1, wx.EXPAND)
        
        # Seed Image
        btn_seed = wx.Button(config_box, label="Pilih Seed Image (Optional)")
        btn_seed.Bind(wx.EVT_BUTTON, lambda e: self.select_seed_image())
        grid_cfg.Add(btn_seed, 0, wx.ALIGN_LEFT)
        self.seed_image_label = wx.StaticText(config_box, label="")
        grid_cfg.Add(self.seed_image_label, 1, wx.EXPAND)
        
        grid_cfg.AddGrowableCol(1, 1)
        config_sizer.Add(grid_cfg, 0, wx.EXPAND | wx.ALL, 5)
        
        self.main_sizer.Add(config_sizer, 0, wx.EXPAND | wx.ALL, 5)
    
    def _setup_google_flow_credentials(self):
        """Setup Google Flow credentials section."""
        self.google_flow_box = wx.StaticBox(self.scrollable_panel, label="Google Flow Credentials")
        google_flow_sizer = wx.StaticBoxSizer(self.google_flow_box, wx.VERTICAL)
        
        google_grid = wx.FlexGridSizer(rows=2, cols=2, vgap=5, hgap=10)
        
        google_grid.Add(wx.StaticText(self.google_flow_box, label="Username:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.google_flow_user_ctrl = wx.TextCtrl(self.google_flow_box, value=self.google_flow_username.get())
        self.google_flow_user_ctrl.Bind(wx.EVT_TEXT, lambda e: self.google_flow_username.set(self.google_flow_user_ctrl.GetValue()))
        google_grid.Add(self.google_flow_user_ctrl, 1, wx.EXPAND)
        
        google_grid.Add(wx.StaticText(self.google_flow_box, label="Password:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.google_flow_pass_ctrl = wx.TextCtrl(self.google_flow_box, value=self.google_flow_password.get(), style=wx.TE_PASSWORD)
        self.google_flow_pass_ctrl.Bind(wx.EVT_TEXT, lambda e: self.google_flow_password.set(self.google_flow_pass_ctrl.GetValue()))
        google_grid.Add(self.google_flow_pass_ctrl, 1, wx.EXPAND)
        
        google_grid.AddGrowableCol(1, 1)
        google_flow_sizer.Add(google_grid, 0, wx.EXPAND | wx.ALL, 5)
        google_flow_sizer.Show(False)
        
        self.main_sizer.Add(google_flow_sizer, 0, wx.EXPAND | wx.ALL, 5)
        self.google_flow_sizer = google_flow_sizer
    
    def _setup_activity_log(self):
        """Setup activity log section."""
        self.main_sizer.Add(wx.StaticText(self.scrollable_panel, label="Activity Log:"), 0, wx.TOP, 10)
        self.log_widget = wx.TextCtrl(self.scrollable_panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.log_widget.SetBackgroundColour(wx.Colour(30, 30, 30))
        self.log_widget.SetForegroundColour(wx.Colour(0, 255, 0))
        self.log_widget.SetFont(wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        self.main_sizer.Add(self.log_widget, 1, wx.EXPAND | wx.ALL, 5)
    
    def _setup_control_buttons(self):
        """Setup control buttons section."""
        ctrl_panel = wx.Panel(self.scrollable_panel)
        ctrl_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.start_btn = wx.Button(ctrl_panel, label="▶ START")
        self.start_btn.SetBackgroundColour(wx.Colour(40, 167, 69))
        self.start_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        self.start_btn.SetFont(wx.Font(10, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.start_btn.Bind(wx.EVT_BUTTON, lambda e: self.start_automation_thread())
        ctrl_sizer.Add(self.start_btn, 1, wx.EXPAND | wx.RIGHT, 5)
        
        self.pause_btn = wx.Button(ctrl_panel, label="⏸ PAUSE")
        self.pause_btn.SetBackgroundColour(wx.Colour(255, 193, 7))
        self.pause_btn.SetForegroundColour(wx.Colour(0, 0, 0))
        self.pause_btn.SetFont(wx.Font(10, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.pause_btn.Disable()
        self.pause_btn.Bind(wx.EVT_BUTTON, lambda e: self.toggle_pause())
        ctrl_sizer.Add(self.pause_btn, 1, wx.EXPAND | wx.RIGHT, 5)
        
        self.stop_btn = wx.Button(ctrl_panel, label="⏹ STOP")
        self.stop_btn.SetBackgroundColour(wx.Colour(220, 53, 69))
        self.stop_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        self.stop_btn.SetFont(wx.Font(10, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.stop_btn.Disable()
        self.stop_btn.Bind(wx.EVT_BUTTON, lambda e: self.stop_automation())
        ctrl_sizer.Add(self.stop_btn, 1, wx.EXPAND)
        
        ctrl_panel.SetSizer(ctrl_sizer)
        self.main_sizer.Add(ctrl_panel, 0, wx.EXPAND | wx.ALL, 10)
    
    # Event handlers
    def select_mode(self, mode):
        """Handle mode selection."""
        self.mode.set(mode)
        if mode == "Sound Relief":
            self.sound_relief_sizer.Show(True)
        else:
            self.sound_relief_sizer.Show(False)
        self.scrollable_panel.Layout()
    
    def select_subcategory(self, subcategory):
        """Handle subcategory selection."""
        self.video_gen_subcategory.set(subcategory)
        self.update_subcategory_ui()
        self.scrollable_panel.Layout()
    
    def update_subcategory_ui(self):
        """Update UI visibility based on selected subcategory."""
        subcategory = self.video_gen_subcategory.get()
        if subcategory == "Default":
            self.gen_method_label.Show()
            self.gen_method_combo.Show()
            self.google_flow_sizer.Show(False)
        elif subcategory == "Flow Video Generator":
            self.gen_method_label.Hide()
            self.gen_method_combo.Hide()
            self.google_flow_sizer.Show(False)
            self.gen_method.set("Flow")
        elif subcategory == "Google Flow":
            self.gen_method_label.Hide()
            self.gen_method_combo.Hide()
            self.google_flow_sizer.Show(True)
            self.gen_method.set("Flow")
        self.scrollable_panel.Layout()
    
    def select_prompt(self):
        """Handle prompt folder selection."""
        path = filedialog.askdirectory("Pilih Folder JSON Prompt")
        if path:
            self.prompt_folder.set(os.path.normpath(path))
            self.prompt_folder_label.SetLabel(self.prompt_folder.get())
            self.prompt_folder_label.Wrap(550)
            self.scrollable_panel.Layout()
    
    def select_seed_image(self):
        """Handle seed image selection."""
        path = filedialog.askopenfilename(
            title="Select Seed Image",
            filetypes=(("Images", "*.png;*.jpg;*.jpeg;*.webp;*.heic;*.avif"), ("All files", "*.*"))
        )
        if path:
            self.seed_image_path.set(os.path.normpath(path))
            self.seed_image_label.SetLabel(os.path.basename(self.seed_image_path.get()))
    
    def toggle_pause(self):
        """Toggle pause/resume."""
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.pause_btn.SetLabel("▶ RESUME")
            self.pause_btn.SetBackgroundColour(wx.Colour(40, 167, 69))
            self.pause_btn.SetForegroundColour(wx.Colour(255, 255, 255))
            self.log("⏸ PAUSED - Klik RESUME untuk melanjutkan")
        else:
            self.pause_btn.SetLabel("⏸ PAUSE")
            self.pause_btn.SetBackgroundColour(wx.Colour(255, 193, 7))
            self.pause_btn.SetForegroundColour(wx.Colour(0, 0, 0))
            self.log("▶ RESUMED")
    
    def stop_automation(self):
        """Stop automation."""
        self.is_paused = False
        self.is_running = False
        self.log("⏹ STOP - Proses dihentikan oleh user")
    
    def log(self, msg):
        """Log a message to the activity log.
        
        Args:
            msg: Message to log (already formatted with timestamp)
        """
        if self.log_widget:
            # Use wx.CallAfter for thread-safe UI updates
            wx.CallAfter(self._append_log, msg + "\n")
        else:
            print(msg)
    
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
                self.youtube_channels.update(saved_channels)
                self.log("✅ YouTube channel settings loaded")
            except Exception as e:
                self.log(f"⚠️ Could not load channel settings: {e}")
    
    def save_youtube_channels(self):
        """Save YouTube channel configuration."""
        config_file = "youtube_channels.json"
        try:
            with open(config_file, 'w') as f:
                json.dump(self.youtube_channels, f, indent=2)
            messagebox.showinfo("Success", "✅ YouTube channel settings saved!")
            self.log("💾 YouTube channel settings saved to youtube_channels.json")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")
            self.log(f"❌ Failed to save channel settings: {e}")
    
    # Automation control
    def start_automation_thread(self):
        """Start automation in a background thread."""
        # Validate inputs
        if not self.prompt_folder.get():
            messagebox.showwarning("Warning", "Silahkan pilih folder JSON prompt terlebih dahulu!")
            return
        if not config.base_download_path:
            messagebox.showwarning("Warning", "DOWNLOAD_PATH tidak ditemukan di .env file!")
            return
        if self.is_running:
            messagebox.showinfo("Info", "Automation sudah berjalan!")
            return
        
        # Mode-specific validations
        if self.mode.get() == "Restorasi":
            intro_path = os.path.join(config.assets_folder, "intro.mp4")
            if not os.path.exists(intro_path):
                response = messagebox.askyesno(
                    "Warning",
                    "intro.mp4 tidak ditemukan di folder Assets.\nLanjutkan tanpa intro?"
                )
                if not response:
                    return
        
        if self.mode.get() == "Sound Relief":
            if not os.path.exists(config.music_folder):
                messagebox.showwarning(
                    "Warning",
                    f"Folder musik tidak ditemukan: {config.music_folder}\nSound Relief membutuhkan file musik MP3!"
                )
                return
        
        # YouTube upload validation
        if self.upload_youtube_var.get():
            current_mode = self.mode.get()
            channel_config = self.youtube_channels.get(current_mode, {})
            if not channel_config.get("name"):
                messagebox.showwarning(
                    "Warning",
                    f"Channel name tidak diset untuk mode '{current_mode}'!\nSilahkan konfigurasi di YouTube Channel Settings."
                )
                return
            credentials_path = channel_config.get("credentials", "")
            if not credentials_path or not os.path.exists(credentials_path):
                messagebox.showwarning(
                    "Warning",
                    f"Credentials file tidak ditemukan untuk mode '{current_mode}'!\nPath: {credentials_path}\nSilahkan konfigurasi di YouTube Channel Settings."
                )
                return
            if not os.path.exists(config.client_secrets):
                messagebox.showwarning(
                    "Warning",
                    f"YouTube client_secrets.json tidak ditemukan!\nPath: {config.client_secrets}"
                )
                return
        
        # Google Flow credentials validation
        if self.video_gen_subcategory.get() == "Google Flow":
            if not self.google_flow_username.get() or not self.google_flow_password.get():
                messagebox.showwarning(
                    "Warning",
                    "Google Flow credentials are required!\nPlease set username and password for Google Flow."
                )
                return
        
        # Log startup info
        self.log("=" * 50)
        self.log("🚀 STARTING AUTOMATION...")
        self.log(f"📂 Prompt Folder: {self.prompt_folder.get()}")
        self.log(f"🎯 Mode: {self.mode.get()}")
        self.log(f"🎬 Generator: {self.generator.get()}")
        self.log(f"⏱️ Timeout: {self.timeout.get()}s")
        self.log(f"🔗 Auto Merge: {'Yes' if self.auto_merge_var.get() else 'No'}")
        self.log(f"🔍 Upscale 4K: {'Yes' if self.upscale_var.get() else 'No'}")
        self.log(f"🧭 Subcategory: {self.video_gen_subcategory.get()}")
        self.log(f"🧭 Generation Method: {self.gen_method.get()}")
        if self.gen_method.get() == "Flow" and self.seed_image_path.get():
            self.log(f"🖼️ Seed Image: {self.seed_image_path.get()}")
        if self.video_gen_subcategory.get() == "Google Flow":
            self.log(f"🔐 Google Flow User: {self.google_flow_username.get()}")
        if self.mode.get() == "Sound Relief":
            self.log(f"🎵 Loop Duration: {self.loop_duration.get()} minutes")
            self.log(f"🎶 Music Folder: {config.music_folder}")
        self.log("=" * 50)
        
        # Update button states
        self.is_running = True
        self.start_btn.Disable()
        self.pause_btn.Enable()
        self.stop_btn.Enable()
        
        # Create generation config
        gen_config = GenerationConfig(
            mode=self.mode.get(),
            generator=self.generator.get(),
            timeout=self.timeout.get(),
            auto_merge=self.auto_merge_var.get(),
            upscale=self.upscale_var.get(),
            upload_youtube=self.upload_youtube_var.get(),
            loop_duration=self.loop_duration.get(),
            gen_method=self.gen_method.get(),
            seed_image_path=self.seed_image_path.get(),
            video_gen_subcategory=self.video_gen_subcategory.get(),
            google_flow_username=self.google_flow_username.get(),
            google_flow_password=self.google_flow_password.get()
        )
        
        # Start pipeline in thread
        threading.Thread(target=self._run_pipeline, args=(gen_config,), daemon=True).start()
    
    def _run_pipeline(self, gen_config: GenerationConfig):
        """Run the pipeline (called from background thread).
        
        Args:
            gen_config: Generation configuration
        """
        try:
            # Create logger with thread-safe callback
            logger = Logger(log_callback=self.log)
            
            # Create and run pipeline
            pipeline = Pipeline(
                gen_config=gen_config,
                prompt_folder=self.prompt_folder.get(),
                youtube_channels=self.youtube_channels,
                logger=logger,
                pause_check=lambda: self.is_paused,
                stop_check=lambda: not self.is_running
            )
            
            pipeline.run()
            
        except Exception as e:
            self.log(f"❌ Pipeline error: {e}")
        finally:
            # Reset button states (thread-safe)
            wx.CallAfter(self._reset_button_states)
    
    def _reset_button_states(self):
        """Reset button states after automation completes."""
        self.is_running = False
        self.start_btn.Enable()
        self.pause_btn.Disable()
        self.pause_btn.SetLabel("⏸ PAUSE")
        self.pause_btn.SetBackgroundColour(wx.Colour(255, 193, 7))
        self.pause_btn.SetForegroundColour(wx.Colour(0, 0, 0))
        self.stop_btn.Disable()
