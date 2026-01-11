import os 
import json 
import threading 
import subprocess 
import time 
import re 
import random 
# ====== WxPython GUI ====== 
import wx 
# ====== Non-GUI imports (tetap seperti aslinya) ====== 
from dotenv import load_dotenv 
from playwright.sync_api import sync_playwright 
# Import custom modules 
from youtube_uploader import YoutubeUploader 
from thumbnail_generator import ThumbnailGenerator 
# -------- Helper: Variable wrapper agar .get()/.set() kompatibel dengan Tkinter -------- 
class SimpleVar: 
    def __init__(self, value=None): 
        self._value = value 
    def get(self): 
        return self._value 
    def set(self, v): 
        self._value = v 
# -------- Helper: messagebox & filedialog wrapper -------- 
class messagebox: 
    @staticmethod 
    def showinfo(title, message): 
        wx.MessageBox(message, title, wx.OK | wx.ICON_INFORMATION) 
    @staticmethod 
    def showwarning(title, message): 
        wx.MessageBox(message, title, wx.OK | wx.ICON_WARNING) 
    @staticmethod 
    def showerror(title, message): 
        wx.MessageBox(message, title, wx.OK | wx.ICON_ERROR) 
    @staticmethod 
    def askyesno(title, message): 
        res = wx.MessageBox(message, title, wx.YES_NO | wx.ICON_WARNING) 
        return res == wx.YES 
class filedialog: 
    @staticmethod 
    def askopenfilename(title="Select File", filetypes=(("All files", "*.*"),)): 
        wildcard = "\n".join([f"{desc}\n{pattern}" for desc, pattern in filetypes]) 
        dlg = wx.FileDialog(None, title, wildcard=wildcard, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) 
        if dlg.ShowModal() == wx.ID_OK: 
            path = dlg.GetPath() 
            dlg.Destroy() 
            return path 
        dlg.Destroy() 
        return "" 
    @staticmethod 
    def askdirectory(title="Select Folder"): 
        dlg = wx.DirDialog(None, title, style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST) 
        if dlg.ShowModal() == wx.ID_OK: 
            path = dlg.GetPath() 
            dlg.Destroy() 
            return path 
        dlg.Destroy() 
        return "" 
# -------- Load .env -------- 
load_dotenv() 
# ========================= 
# KELAS APLIKASI (wxPython) 
# ========================= 
class NexabotApp(wx.Frame): 
    def __init__(self, parent=None, title="Glidly Pro - AI Automator (Enhanced)"): 
        super().__init__(parent, title=title, size=(900, 700)) 
        self.SetMinSize(wx.Size(800, 600)) 
        # ====== SCROLLABLE ROOT (wx.ScrolledWindow) ====== 
        self.scrollable_panel = wx.ScrolledWindow(self, style=wx.VSCROLL) 
        self.scrollable_panel.SetScrollRate(10, 10) 
        self.main_sizer = wx.BoxSizer(wx.VERTICAL) 
        self.scrollable_panel.SetSizer(self.main_sizer) 
        # ====== Load config vars (logika tetap sama) ====== 
        self.email = os.getenv("GLID_EMAIL") 
        self.pwd = os.getenv("GLID_PWD") 
        self.base_download_path = os.path.normpath(os.getenv("DOWNLOAD_PATH")) if os.getenv("DOWNLOAD_PATH") else None 
        self.ffmpeg_path = os.path.normpath(os.getenv("FFMPEG_EXE")) if os.getenv("FFMPEG_EXE") else "ffmpeg" 
        self.assets_folder = os.path.normpath(os.getenv("ASSETS_FOLDER", "./Assets")) 
        # MUSIC_FOLDER dari .env (default: ./Assets/music) 
        self.music_folder = os.path.normpath(os.getenv("MUSIC_FOLDER", os.path.join(self.assets_folder, "music"))) 
        # YouTube API paths 
        self.client_secrets = os.getenv("YT_CLIENT_SECRETS", "client_secrets.json") 
        self.credentials_file = os.getenv("YT_CREDENTIALS", "token.json") 
        # ====== "Tkinter-like" variables ====== 
        self.prompt_folder = SimpleVar("") 
        self.mode = SimpleVar("Shorts") 
        self.generator = SimpleVar("Veo 3.1") 
        self.timeout = SimpleVar(180) 
        self.auto_merge_var = SimpleVar(True) 
        self.upscale_var = SimpleVar(False) 
        self.upload_youtube_var = SimpleVar(False) 
        self.loop_duration = SimpleVar(60) 
        # [FLOW] Generation method + seed image + start account index 
        self.gen_method = SimpleVar("Default")  # Default | Flow | Google Flow 
        self.seed_image_path = SimpleVar("") 
        self.flow_account_start = SimpleVar(int(os.getenv("FLOW_ACCOUNT_START", "8"))) 
        # [GOOGLE FLOW] Credentials 
        self.google_flow_username = SimpleVar("") 
        self.google_flow_password = SimpleVar("") 
        # Subcategory for Video Generator 
        self.video_gen_subcategory = SimpleVar("Default")  # Default | Flow Video Generator | Google Flow 
        # Livestream settings
        self.livestream_title = SimpleVar("")
        self.livestream_description = SimpleVar("")
        self.livestream_privacy = SimpleVar("public")
        self.livestream_delay_minutes = SimpleVar(5)
        # YouTube Channel mapping per mode 
        self.youtube_channels = { 
            "Shorts": {"name": "", "credentials": ""}, 
            "Sound Relief": {"name": "", "credentials": ""}, 
            "Restorasi": {"name": "", "credentials": ""}, 
            "Home Renovation": {"name": "", "credentials": ""} 
        } 
        # Pause control 
        self.is_paused = False 
        self.is_running = False 
        self.is_stopping = False  # New state to track stopping process
        self.pipeline_thread = None  # Track the automation thread
        # UI refs 
        self.log_widget = None 
        self.sound_relief_box = None 
        # Build UI 
        self.setup_ui() 
        # Load channels (menggunakan log() -> kini sudah ada log_widget) 
        self.load_youtube_channels() 
    # ========================= 
    # SETUP UI (wxPython) 
    # ========================= 
    def setup_ui(self): 
        # Title 
        title = wx.StaticText(self.scrollable_panel, label="GLIDLY AI AUTOMATOR") 
        title_font = wx.Font(16, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD) 
        title.SetFont(title_font) 
        self.main_sizer.Add(title, 0, wx.TOP | wx.BOTTOM | wx.ALIGN_CENTER_HORIZONTAL, 10) 
        # ---- Path Settings ---- 
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
        # ---- Mode Selection ---- 
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
        # ---- Sound Relief Options (dinamis: show/hide) ---- 
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
        # ---- Video Generator Subcategory Selection ---- 
        subcategory_box = wx.StaticBox(self.scrollable_panel, label="Video Generator Type") 
        subcategory_sizer = wx.StaticBoxSizer(subcategory_box, wx.HORIZONTAL) 
        subcategories = ["Default", "Nexa", "Flow Video Generator", "Google Flow"] 
        lbl_subcat = wx.StaticText(subcategory_box, label="Select Type:") 
        self.subcategory_combo = wx.ComboBox(subcategory_box, choices=subcategories, style=wx.CB_READONLY, size=(200, -1)) 
        self.subcategory_combo.SetValue(self.video_gen_subcategory.get()) 
        self.subcategory_combo.Bind(wx.EVT_COMBOBOX, lambda e: self.select_subcategory(self.subcategory_combo.GetValue())) 
        subcategory_sizer.Add(lbl_subcat, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5) 
        subcategory_sizer.Add(self.subcategory_combo, 1, wx.ALL | wx.EXPAND, 5) 
        self.main_sizer.Add(subcategory_sizer, 0, wx.EXPAND | wx.ALL, 5) 
        # ---- Configurations ---- 
        config_box = wx.StaticBox(self.scrollable_panel, label="Configurations") 
        config_sizer = wx.StaticBoxSizer(config_box, wx.VERTICAL) 
        grid_cfg = wx.FlexGridSizer(rows=8, cols=2, vgap=5, hgap=10) 
        grid_cfg.Add(wx.StaticText(config_box, label="Generator:"), 0, wx.ALIGN_CENTER_VERTICAL) 
        self.generator_combo = wx.ComboBox(config_box, choices=["Veo 3.1", "Nexa Gen", "Sora 2"], style=wx.CB_READONLY) 
        self.generator_combo.SetValue(self.generator.get()) 
        self.generator_combo.Bind(wx.EVT_COMBOBOX, lambda e: self.generator.set(self.generator_combo.GetValue())) 
        grid_cfg.Add(self.generator_combo, 1, wx.EXPAND) 
        grid_cfg.Add(wx.StaticText(config_box, label="Timeout (sec):"), 0, wx.ALIGN_CENTER_VERTICAL) 
        self.timeout_spin = wx.SpinCtrl(config_box, min=10, max=36000, initial=self.timeout.get()) 
        self.timeout_spin.Bind(wx.EVT_SPINCTRL, lambda e: self.timeout.set(self.timeout_spin.GetValue())) 
        grid_cfg.Add(self.timeout_spin, 1, wx.EXPAND) 
        self.auto_merge_cb = wx.CheckBox(config_box, label="Auto Merge Video") 
        self.auto_merge_cb.SetValue(self.auto_merge_var.get()) 
        self.auto_merge_cb.Bind(wx.EVT_CHECKBOX, lambda e: self.auto_merge_var.set(self.auto_merge_cb.GetValue())) 
        grid_cfg.Add(self.auto_merge_cb, 0, wx.ALIGN_LEFT) 
        grid_cfg.AddSpacer(0) 
        self.upscale_cb = wx.CheckBox(config_box, label="Upscale to 4K") 
        self.upscale_cb.SetValue(self.upscale_var.get()) 
        self.upscale_cb.Bind(wx.EVT_CHECKBOX, lambda e: self.upscale_var.set(self.upscale_cb.GetValue())) 
        grid_cfg.Add(self.upscale_cb, 0, wx.ALIGN_LEFT) 
        grid_cfg.AddSpacer(0) 
        # [FLOW] Seed Image 
        btn_seed = wx.Button(config_box, label="Pilih Seed Image (Optional)") 
        btn_seed.Bind(wx.EVT_BUTTON, lambda e: self.select_seed_image()) 
        grid_cfg.Add(btn_seed, 0, wx.ALIGN_LEFT) 
        self.seed_image_label = wx.StaticText(config_box, label="") 
        grid_cfg.Add(self.seed_image_label, 1, wx.EXPAND) 
        grid_cfg.AddGrowableCol(1, 1) 
        config_sizer.Add(grid_cfg, 0, wx.EXPAND | wx.ALL, 5) 
        self.main_sizer.Add(config_sizer, 0, wx.EXPAND | wx.ALL, 5) 
        # ---- Google Flow Credentials (show/hide based on subcategory) ---- 
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
        # ---- Livestream Settings ---- 
        livestream_box = wx.StaticBox(self.scrollable_panel, label="YouTube Livestream") 
        livestream_sizer = wx.StaticBoxSizer(livestream_box, wx.VERTICAL) 
        livestream_grid = wx.FlexGridSizer(rows=4, cols=2, vgap=5, hgap=10) 
        
        livestream_grid.Add(wx.StaticText(livestream_box, label="Title:"), 0, wx.ALIGN_CENTER_VERTICAL) 
        self.livestream_title_ctrl = wx.TextCtrl(livestream_box) 
        self.livestream_title_ctrl.Bind(wx.EVT_TEXT, lambda e: self.livestream_title.set(self.livestream_title_ctrl.GetValue())) 
        livestream_grid.Add(self.livestream_title_ctrl, 1, wx.EXPAND) 
        
        livestream_grid.Add(wx.StaticText(livestream_box, label="Description:"), 0, wx.ALIGN_CENTER_VERTICAL) 
        self.livestream_desc_ctrl = wx.TextCtrl(livestream_box, style=wx.TE_MULTILINE, size=(-1, 60)) 
        self.livestream_desc_ctrl.Bind(wx.EVT_TEXT, lambda e: self.livestream_description.set(self.livestream_desc_ctrl.GetValue())) 
        livestream_grid.Add(self.livestream_desc_ctrl, 1, wx.EXPAND) 
        
        livestream_grid.Add(wx.StaticText(livestream_box, label="Privacy:"), 0, wx.ALIGN_CENTER_VERTICAL) 
        self.livestream_privacy_combo = wx.ComboBox(livestream_box, choices=["public", "private", "unlisted"], style=wx.CB_READONLY) 
        self.livestream_privacy_combo.SetValue(self.livestream_privacy.get()) 
        self.livestream_privacy_combo.Bind(wx.EVT_COMBOBOX, lambda e: self.livestream_privacy.set(self.livestream_privacy_combo.GetValue())) 
        livestream_grid.Add(self.livestream_privacy_combo, 1, wx.EXPAND) 
        
        livestream_grid.Add(wx.StaticText(livestream_box, label="Start Delay (min):"), 0, wx.ALIGN_CENTER_VERTICAL) 
        self.livestream_delay_spin = wx.SpinCtrl(livestream_box, min=1, max=1440, initial=self.livestream_delay_minutes.get()) 
        self.livestream_delay_spin.Bind(wx.EVT_SPINCTRL, lambda e: self.livestream_delay_minutes.set(self.livestream_delay_spin.GetValue())) 
        livestream_grid.Add(self.livestream_delay_spin, 1, wx.EXPAND) 
        
        livestream_grid.AddGrowableCol(1, 1) 
        livestream_sizer.Add(livestream_grid, 0, wx.EXPAND | wx.ALL, 5) 
        
        # Create Broadcast button 
        btn_create_broadcast = wx.Button(livestream_box, label="📡 Create Livestream Broadcast") 
        btn_create_broadcast.Bind(wx.EVT_BUTTON, lambda e: self.create_livestream_broadcast()) 
        livestream_sizer.Add(btn_create_broadcast, 0, wx.EXPAND | wx.ALL, 5) 
        
        self.main_sizer.Add(livestream_sizer, 0, wx.EXPAND | wx.ALL, 5) 
        # ---- Activity Log ---- 
        self.main_sizer.Add(wx.StaticText(self.scrollable_panel, label="Activity Log:"), 0, wx.TOP, 10) 
        self.log_widget = wx.TextCtrl(self.scrollable_panel, style=wx.TE_MULTILINE | wx.TE_READONLY) 
        self.log_widget.SetBackgroundColour(wx.Colour(30, 30, 30)) 
        self.log_widget.SetForegroundColour(wx.Colour(0, 255, 0)) 
        self.log_widget.SetFont(wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)) 
        self.main_sizer.Add(self.log_widget, 1, wx.EXPAND | wx.ALL, 5) 
        # ---- Control Buttons ---- 
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
        # Finish layout 
        self.scrollable_panel.Layout() 
        # Sembunyikan dynamic frames di awal 
        self.sound_relief_sizer.Show(False) 
        self.google_flow_sizer.Show(False) 
        # Initialize subcategory UI 
        self.update_subcategory_ui() 
        self.scrollable_panel.Layout() 
    # ========================= 
    # Fungsi GUI → sama perilaku 
    # ========================= 
    def select_mode(self, mode): 
        self.mode.set(mode) 
        if mode == "Sound Relief": 
            self.sound_relief_sizer.Show(True) 
        else: 
            self.sound_relief_sizer.Show(False) 
        self.scrollable_panel.Layout() 
    def select_subcategory(self, subcategory): 
        self.video_gen_subcategory.set(subcategory) 
        self.update_subcategory_ui() 
        self.scrollable_panel.Layout() 
    def update_subcategory_ui(self): 
        """Update UI visibility based on selected subcategory""" 
        subcategory = self.video_gen_subcategory.get() 
        if subcategory in ["Default", "Nexa"]: 
            # Default and Nexa use standard UI
            self.google_flow_sizer.Show(False) 
        elif subcategory == "Flow Video Generator": 
            # Flow Video Generator uses standard UI
            self.google_flow_sizer.Show(False) 
        elif subcategory == "Google Flow": 
            # Show Google Flow credentials 
            self.google_flow_sizer.Show(True) 
        self.scrollable_panel.Layout() 
    def load_youtube_channels(self): 
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
        config_file = "youtube_channels.json" 
        try: 
            with open(config_file, 'w') as f: 
                json.dump(self.youtube_channels, f, indent=2) 
            messagebox.showinfo("Success", "✅ YouTube channel settings saved!") 
            self.log("💾 YouTube channel settings saved to youtube_channels.json") 
        except Exception as e: 
            messagebox.showerror("Error", f"Failed to save settings: {e}") 
            self.log(f"❌ Failed to save channel settings: {e}") 
    def log(self, msg): 
        timestamp = time.strftime('%H:%M:%S') 
        line = f"[{timestamp}] {msg}\n" 
        if self.log_widget and self.log_widget: 
            self.log_widget.AppendText(line) 
        else: 
            print(line) 
    def select_prompt(self): 
        path = filedialog.askdirectory("Pilih Folder JSON Prompt") 
        if path: 
            self.prompt_folder.set(os.path.normpath(path)) 
            self.prompt_folder_label.SetLabel(self.prompt_folder.get()) 
            self.prompt_folder_label.Wrap(550) 
            self.scrollable_panel.Layout() 
    def select_seed_image(self): 
        path = filedialog.askopenfilename( 
            title="Select Seed Image", 
            filetypes=(("Images", "*.png;*.jpg;*.jpeg;*.webp;*.heic;*.avif"), ("All files", "*.*")) 
        ) 
        if path: 
            self.seed_image_path.set(os.path.normpath(path)) 
            self.seed_image_label.SetLabel(os.path.basename(self.seed_image_path.get())) 
    
    def create_livestream_broadcast(self):
        """Create a YouTube livestream broadcast"""
        from datetime import datetime, timezone, timedelta
        
        # Validate inputs
        title = self.livestream_title.get().strip()
        if not title:
            messagebox.showwarning("Warning", "Please enter a title for the livestream!")
            return
        
        description = self.livestream_description.get().strip()
        if not description:
            description = title  # Use title as description if not provided
        
        privacy = self.livestream_privacy.get()
        delay_minutes = self.livestream_delay_minutes.get()
        
        # Check for client secrets
        if not os.path.exists(self.client_secrets):
            messagebox.showerror(
                "Error",
                f"YouTube client_secrets.json not found!\nPath: {self.client_secrets}"
            )
            return
        
        # Calculate scheduled start time
        now_utc = datetime.now(timezone.utc)
        scheduled_dt = now_utc + timedelta(minutes=delay_minutes)
        scheduled_start_time = scheduled_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        try:
            self.log(f"📡 Creating livestream broadcast: {title}")
            self.log(f"   🕒 Scheduled Start: {scheduled_start_time}")
            self.log(f"   🔒 Privacy: {privacy}")
            
            # Use YoutubeUploader to create broadcast
            uploader = YoutubeUploader(self.client_secrets, self.credentials_file)
            result = uploader.create_broadcast(
                title=title,
                description=description,
                privacy_status=privacy,
                scheduled_start_time=scheduled_start_time
            )
            
            self.log(f"✅ Broadcast created successfully!")
            self.log(f"   Broadcast ID: {result['broadcast_id']}")
            self.log(f"   Stream URL: {result['stream_url']}")
            self.log(f"   Stream Key: {result['stream_key']}")
            
            messagebox.showinfo(
                "Success",
                f"Livestream broadcast created!\n\n"
                f"Broadcast ID: {result['broadcast_id']}\n"
                f"Stream URL: {result['stream_url']}\n\n"
                f"Use these details to configure your streaming software."
            )
            
        except Exception as e:
            self.log(f"❌ Failed to create broadcast: {e}")
            messagebox.showerror("Error", f"Failed to create livestream:\n{str(e)}")
    
    def toggle_pause(self): 
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
        self.is_paused = False 
        self.is_running = False 
        self.is_stopping = True
        self.start_btn.Disable()  # Keep START disabled during stopping
        self.log("⏹ STOP - Stopping automation...")
        # Start a background thread to wait for cleanup and then enable START
        threading.Thread(target=self._wait_for_cleanup, daemon=True).start()
    
    def _wait_for_cleanup(self):
        """Wait for pipeline thread to finish and then re-enable START button"""
        if self.pipeline_thread and self.pipeline_thread.is_alive():
            # Wait for thread to finish with timeout
            self.pipeline_thread.join(timeout=30)
        self.is_stopping = False
        # Re-enable START button on UI thread
        wx.CallAfter(self._cleanup_complete)
    
    def _cleanup_complete(self):
        """Called when cleanup is complete to reset UI state"""
        self.start_btn.Enable()
        self.pause_btn.Disable()
        self.pause_btn.SetLabel("⏸ PAUSE")
        self.pause_btn.SetBackgroundColour(wx.Colour(255, 193, 7))
        self.pause_btn.SetForegroundColour(wx.Colour(0, 0, 0))
        self.stop_btn.Disable()
        self.log("✅ Automation stopped - Ready to start again")
    # =========================
    # LOGIC (dipertahankan + helper baru) 
    # ========================= 
    def check_processed_videos(self, folder_path, total_prompts): 
        processed = set() 
        if not os.path.exists(folder_path): 
            return processed 
        for filename in os.listdir(folder_path): 
            if filename.endswith(".mp4") and filename.split('.')[0].isdigit(): 
                scene_id = int(filename.split('.')[0]) 
                if scene_id <= total_prompts: 
                    processed.add(scene_id) 
        return processed 
    def compute_generation_status(self, folder_path, total_prompts): 
        present = set() 
        for filename in os.listdir(folder_path): 
            if re.match(r'^\d+\.mp4$', filename): 
                present.add(int(filename.split('.')[0])) 
        missing = [i for i in range(1, total_prompts + 1) if i not in present] 
        return sorted(present), missing 
    def upscale_video(self, input_path, output_path): 
        self.log("🔍 Upscaling video to 4K...") 
        cmd = [ 
            self.ffmpeg_path, '-i', input_path, 
            '-vf', 'scale=3840:2160:flags=lanczos', 
            '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', 
            '-c:a', 'copy', 
            output_path, '-y' 
        ] 
        try: 
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT) 
            self.log(f"✅ Upscale Success: {os.path.basename(output_path)}") 
            return output_path 
        except Exception as e: 
            self.log(f"❌ Upscale Failed: {e}") 
            return None 
    def create_sound_relief_video(self, folder_path, duration_minutes): 
        self.log(f"🎵 Creating Sound Relief video ({duration_minutes} minutes)...") 
        video_files = sorted([f for f in os.listdir(folder_path)
                              if f.endswith(".mp4") and f.split('.')[0].isdigit()],
                             key=lambda x: int(x.split('.')[0]))
        if not video_files:
            self.log("❌ No video files found for Sound Relief")
            return None
        list_path = os.path.join(folder_path, "temp_concat.txt")
        with open(list_path, "w") as f:
            for v in video_files:
                f.write(f"file '{v}'\n")
        base_video = os.path.join(folder_path, "base_sequence.mp4")
        subprocess.run([
            self.ffmpeg_path, '-f', 'concat', '-safe', '0', '-i', list_path,
            '-c', 'copy', base_video, '-y'
        ], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        probe_cmd = [self.ffmpeg_path, '-i', base_video, '-f', 'null', '-']
        result = subprocess.run(probe_cmd, capture_output=True, text=True)
        duration_match = re.search(r'Duration:\s+(\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?', result.stderr)
        base_duration_sec = 10
        if duration_match:
            h, m, s = map(int, duration_match.groups()[:3])
            frac = duration_match.group(4)
            base_duration_sec = h * 3600 + m * 60 + s + (int(frac) / (10 ** len(frac)) if frac else 0)
        target_duration_sec = duration_minutes * 60
        loop_count = max(1, int(target_duration_sec / base_duration_sec) + 1)
        looped_video = os.path.join(folder_path, "looped_video.mp4")
        subprocess.run([
            self.ffmpeg_path, '-stream_loop', str(loop_count - 1), '-i', base_video,
            '-filter_complex', f'concat=n={loop_count}:v=1:a=0,trim=duration={target_duration_sec}[v]',
            '-map', '[v]', '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
            looped_video, '-y'
        ], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        music_dir = self.music_folder
        music_files = [f for f in os.listdir(music_dir) if f.lower().endswith('.mp3')] if os.path.exists(music_dir) else []
        if music_files:
            music_path = os.path.join(music_dir, random.choice(music_files))
            final_output = os.path.join(folder_path, "FINAL_SOUND_RELIEF.mp4")
            self.log(f"🎶 Adding music from {music_dir}: {os.path.basename(music_path)}")
            subprocess.run([
                self.ffmpeg_path, '-i', looped_video, '-stream_loop', '-1', '-i', music_path,
                '-shortest', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
                final_output, '-y'
            ], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            if os.path.exists(looped_video):
                os.remove(looped_video)
        else:
            final_output = looped_video
            self.log(f"⚠️ No music files found in {music_dir}")
        if os.path.exists(list_path): os.remove(list_path)
        if os.path.exists(base_video): os.remove(base_video)
        self.log(f"✅ Sound Relief video created: {os.path.basename(final_output)}")
        return final_output
    def merge_with_intro(self, folder_path): 
        intro_path = os.path.join(self.assets_folder, "intro.mp4") 
        if not os.path.exists(intro_path): 
            self.log("⚠️ intro.mp4 not found in Assets folder, skipping intro") 
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
            self.log(f"✅ Merged with intro: {os.path.basename(output_path)}")
            if os.path.exists(list_path): os.remove(list_path)
            return output_path
        except Exception as e:
            self.log(f"❌ Merge Failed: {e}")
            return None
    def merge_process(self, folder_path): 
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
            self.log(f"✅ Merge Success: {os.path.basename(output_path)}")
            if os.path.exists(list_path): os.remove(list_path)
            return output_path
        except Exception as e:
            self.log(f"❌ Merge Failed: {e}")
            return None
    def upload_to_youtube(self, video_path, title, mode): 
        try: 
            channel_config = self.youtube_channels.get(mode, {}) 
            channel_name = channel_config.get("name", "Unknown Channel") 
            credentials_path = channel_config.get("credentials", "") 
            if not credentials_path or not os.path.exists(credentials_path): 
                self.log(f"❌ Credentials file not found for mode '{mode}'") 
                self.log(f" Expected: {credentials_path}") 
                messagebox.showwarning( 
                    "Upload Failed", 
                    f"Credentials file not found for {mode} mode!\nPlease configure in YouTube Channel Settings." 
                ) 
                return None 
            self.log(f"📤 Uploading to YouTube Channel: {channel_name}") 
            self.log(f" Using credentials: {os.path.basename(credentials_path)}") 
            uploader = YoutubeUploader(self.client_secrets, credentials_path) 
            description = f"Video generated using Glidly Pro AI Automator\nMode: {mode}\nChannel: {channel_name}" 
            tags = "AI,automation,video" 
            thumbnail_path = None 
            if mode == "Restorasi": 
                self.log("🖼️ Generating thumbnail...") 
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
            self.log(f"✅ YouTube Upload Complete!") 
            self.log(f" Channel: {channel_name}") 
            self.log(f" Video ID: {video_id}") 
            self.log(f" URL: https://youtube.com/watch?v={video_id}") 
            return video_id 
        except Exception as e: 
            self.log(f"❌ YouTube Upload Failed: {str(e)}") 
            messagebox.showerror("Upload Error", f"Failed to upload to YouTube:\n{str(e)}") 
            return None 
    # ----- Helper: pilih page berdasarkan URL di semua tab ----- 
    def wait_for_url_in_any_page(self, context, pattern, timeout_ms): 
        end = time.time() + timeout_ms / 1000.0 
        compiled = re.compile(pattern) 
        while time.time() < end: 
            for p in context.pages: 
                url = getattr(p, "url", "") or "" 
                if compiled.search(url): 
                    try: 
                        p.bring_to_front() 
                    except Exception: 
                        pass 
                    return p 
            time.sleep(0.25) 
        raise TimeoutError(f"No page matched URL pattern: {pattern}") 
    # ----- Helper: cek apakah sudah di halaman Video Generator ----- 
    def is_on_videogenerator(self, page): 
        try: 
            return page.locator("h1", has_text="Video Generator").first.is_visible() 
        except Exception: 
            return False 
    # ----- Helper: lakukan login di halaman login ----- 
    def perform_login(self, page): 
        try: 
            self.log("🔐 Login required — filling credentials...") 
            if page.locator("#email").is_visible(): 
                page.fill("#email", self.email or "") 
                page.keyboard.press("Enter") 
                page.wait_for_selector("#password", timeout=15000) 
                page.fill("#password", self.pwd or "") 
                page.keyboard.press("Enter") 
                self.log("✅ Login submitted.") 
                return True 
        except Exception as e: 
            self.log(f"❌ Login form error: {e}") 
        return False 
    # ----- NEW: Clear Queue + ensure no processing cards (Default path) ----- 
    def clear_queue_if_present(self, page, timeout_ms=5000): 
        try: 
            def _accept_dialog(dialog): 
                try: 
                    dialog.accept() 
                except Exception: 
                    pass 
            page.once("dialog", _accept_dialog) 
            btn = page.locator("button:has-text('Clear Queue')").first 
            if btn.is_visible(): 
                self.log("🧹 Queue: tombol 'Clear Queue' terdeteksi — eksekusi...") 
                btn.click(timeout=timeout_ms) 
                time.sleep(1.0) 
                self.log("✅ Queue dibersihkan (dialog dikonfirmasi).") 
                return True 
            else: 
                self.log("ℹ️ 'Clear Queue' tidak terlihat pada halaman saat ini.") 
                return False 
        except Exception as e: 
            self.log(f"⚠️ Gagal klik 'Clear Queue': {str(e)[:120]}") 
            return False 
    def wait_until_no_processing_cards(self, page, timeout_ms=15000): 
        end = time.time() + timeout_ms / 1000.0 
        while time.time() < end: 
            try: 
                has_processing = False 
                if page.locator(r"text=/Processing|In\s+Queue|Generating/i").is_visible(): 
                    has_processing = True 
                if page.locator('[role="status"], [role="progressbar"], [aria-busy="true"]').is_visible(): 
                    has_processing = True 
                if page.locator("button:has-text('Cancel'), button:has-text('Stop')").is_visible(): 
                    has_processing = True 
                if not has_processing: 
                    return True 
            except Exception: 
                return True 
            time.sleep(0.5) 
        return False 

    # =========================
    # MAIN AUTOMATION (Default)
    # =========================
    def run_automator_logic(self):
        self.is_running = True
        self.start_btn.Disable()
        self.pause_btn.Enable()
        self.stop_btn.Enable()
        
        # Check if we should use extensions based on subcategory
        use_extensions = self.video_gen_subcategory.get() == "Default"
        ext_path = os.path.abspath("nexa_extension")
        target_generator_url = "https://nexabot.pro/dashboard/videogenerator"
        context = None
        
        if use_extensions:
            self.log("🔌 Extensions enabled (Default mode)")
        else:
            self.log("🚫 Extensions disabled (Nexa mode)")
        
        try:
            with sync_playwright() as p:
                self.log("🌐 Membuka Browser...")
                
                # Conditionally add extension args
                if use_extensions:
                    context = p.chromium.launch_persistent_context(
                        user_data_dir="user_data", headless=False, slow_mo=1000,
                        args=[f"--disable-extensions-except={ext_path}", f"--load-extension={ext_path}"],
                    )
                else:
                    context = p.chromium.launch_persistent_context(
                        user_data_dir="user_data", headless=False, slow_mo=1000,
                    )
                
                context.set_default_timeout(self.timeout.get() * 1000)
                page = context.new_page()
                
                # Only try to configure extension if using extensions
                if use_extensions:
                    try:
                        if context.service_workers:
                            actual_ext_id = context.service_workers[0].url.split("/")[2]
                            page.goto(f"chrome-extension://{actual_ext_id}/popup.html")
                            email_f = page.locator("#emailInput")
                            if email_f.is_visible():
                                email_f.fill(self.email or "")
                                page.fill("#passwordInput", self.pwd or "")
                                page.keyboard.press("Enter")
                                time.sleep(2)
                                if page.locator("#startBtn").is_visible():
                                    page.click("#startBtn")
                    except Exception:
                        pass
                
                self.log("➡️ Navigating directly to Video Generator...")
                page.goto(target_generator_url, wait_until="domcontentloaded")
                if not self.is_on_videogenerator(page):
                    self.log("ℹ️ Video Generator heading not visible — checking login form...")
                    need_login = False
                    try:
                        need_login = page.locator("#email").is_visible()
                    except Exception:
                        need_login = True
                    if need_login:
                        if not self.perform_login(page):
                            self.is_running = False
                            return
                    self.log("➡️ Post-login — redirecting to Video Generator...")
                    try:
                        page.goto(target_generator_url, wait_until="domcontentloaded")
                    except Exception:
                        pass
                try:
                    page = self.wait_for_url_in_any_page(
                        context, r".*/dashboard/videogenerator.*", self.timeout.get() * 1000
                    )
                except Exception:
                    found = False
                    for p2 in context.pages:
                        if self.is_on_videogenerator(p2):
                            page = p2
                            found = True
                            break
                    if not found:
                        self.log("❌ Could not reach Video Generator after login.")
                        self.is_running = False
                        return
                if self.is_on_videogenerator(page):
                    self.log("✅ Video Generator ready after login.")
                else:
                    self.log("⚠️ Video Generator still not visible — attempting dashboard link fallback...")
                    try:
                        page.click('a[href="/dashboard/videogenerator"]', timeout=self.timeout.get() * 1000)
                        page = self.wait_for_url_in_any_page(
                            context, r".*/dashboard/videogenerator.*", self.timeout.get() * 1000
                        )
                        if self.is_on_videogenerator(page):
                            self.log("✅ Video Generator opened via dashboard link.")
                        else:
                            raise Exception("Heading not found after dashboard link.")
                    except Exception as e:
                        self.log(f"❌ Fallback failed: {e}")
                        self.is_running = False
                        return
                # ---- Loop JSON prompts ----
                for json_file in sorted(os.listdir(self.prompt_folder.get())):
                    if not self.is_running:
                        self.log("⏹ Automation stopped by user")
                        break
                    if not json_file.endswith(".json"):
                        continue
                    save_dir = os.path.join(self.base_download_path, os.path.splitext(json_file)[0])
                    os.makedirs(save_dir, exist_ok=True)
                    with open(os.path.join(self.prompt_folder.get(), json_file), 'r', encoding='utf-8') as f:
                        data_json = json.load(f)
                    total_scenes = len(data_json)
                    self.log(f"📁 Processing: {json_file} (total scenes: {total_scenes})")
                    processed_scenes = self.check_processed_videos(save_dir, total_scenes)
                    if processed_scenes:
                        self.log(f"⏭️ Skipping {len(processed_scenes)} already processed scenes")
                    last_frame_path = None
                    for i, item in enumerate(data_json, 1):
                        while self.is_paused and self.is_running:
                            time.sleep(1)
                        if not self.is_running:
                            break
                        if i in processed_scenes:
                            self.log(f"⏭️ Scene #{i} already exists, skipping...")
                            video_path = os.path.join(save_dir, f"{i}.mp4")
                            if os.path.exists(video_path):
                                temp_frame = os.path.join(save_dir, f"last_frame_{i}.jpg")
                                subprocess.run([self.ffmpeg_path, '-sseof', '-1', '-i', video_path,
                                                '-update', '1', '-q:v', '2', '-frames:v', '1',
                                                temp_frame, '-y'],
                                               stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
                                last_frame_path = temp_frame
                            continue
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
                        try:
                            gen_target = self.generator.get()
                            self.log(f"🎬 Scene #{i}: Selecting {gen_target}...")
                            gen_grid = page.locator("div.grid-cols-3").first
                            gen_grid.locator("button", has_text=gen_target).first.click(timeout=5000)
                            if gen_target == "Veo 3.1":
                                booster_card = page.locator("div.rounded-xl").filter(has_text="Veo 3.1 Booster").last
                                status_text = booster_card.inner_text(timeout=5000)
                                if "Enabled" not in status_text:
                                    if "Active" in status_text:
                                        booster_card.click()
                                        self.log("⚡ Booster: Enabled")
                                    else:
                                        self.log("🔄 Booster: Refreshing...")
                                        page.locator("button:has-text('Refresh Status')").click()
                                        time.sleep(5)
                                        if "Active" in booster_card.inner_text():
                                            booster_card.click()
                            ratio = "Vertical (9:16)" if self.mode.get() == "Shorts" else "Landscape (16:9)"
                            page.locator("button").filter(has_text=ratio).click()
                            if last_frame_path and os.path.exists(last_frame_path):
                                self.log("🖼️ I2V: Uploading start frame...")
                                page.set_input_files("input[accept='image/*']", last_frame_path)
                                time.sleep(2)
                            self.log(f"✍️ Scene #{i}: Filling prompt...")
                            textarea = page.locator("textarea[placeholder*='Describe your video']")
                            textarea.scroll_into_view_if_needed()
                            textarea.fill(prompt_text)
                            self.log(f"🎥 Scene #{i}: Generating...")
                            page.locator("button:has-text('Generate Video')").click()
                            self.log(f"⏳ Scene #{i}: Waiting for result...")
                            try:
                                page.wait_for_selector("button:has-text('Download')",
                                                       timeout=self.timeout.get() * 1000)
                                with page.expect_download() as dl_info:
                                    page.click("button:has-text('Download')")
                                video_path = os.path.join(save_dir, f"{i}.mp4")
                                dl_info.value.save_as(video_path)
                                self.log(f"✅ Scene #{i}: SUCCESS")
                                temp_frame = os.path.join(save_dir, f"last_frame_{i}.jpg")
                                subprocess.run([self.ffmpeg_path, '-sseof', '-1', '-i', video_path,
                                                '-update', '1', '-q:v', '2', '-frames:v', '1',
                                                temp_frame, '-y'],
                                               stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
                                last_frame_path = temp_frame
                                page.click('button[title="Delete video"]')
                                page.wait_for_selector("button:has-text('Download')", state="hidden")
                                self.log(f"🗑️ Scene #{i}: Card cleared")
                            except Exception as e:
                                self.log(f"❌ Scene #{i} FAILED: {str(e)[:150]}")
                                last_frame_path = None
                                self.log("🧹 Timeout pada 'Download' — mencoba 'Clear Queue'...")
                                cleared = self.clear_queue_if_present(page)
                                ui_clean = self.wait_until_no_processing_cards(page, timeout_ms=15000)
                                if cleared and ui_clean:
                                    self.log("✅ Queue cleared & UI bersih — lanjut ke scene berikutnya.")
                                elif cleared and not ui_clean:
                                    self.log("⚠️ Queue cleared, namun indikator processing masih terlihat setelah waktu tunggu.")
                                elif not cleared and ui_clean:
                                    self.log("⚠️ 'Clear Queue' tidak ditemukan/berhasil, tetapi UI sudah bersih — lanjut.")
                                else:
                                    self.log("⚠️ 'Clear Queue' gagal dan UI masih menunjukkan processing — lanjut dengan kehati-hatian.")
                        except Exception as e:
                            self.log(f"❌ Scene #{i} FAILED: {str(e)[:100]}")
                            last_frame_path = None
                    generated_ids, missing_ids = self.compute_generation_status(save_dir, total_scenes)
                    if missing_ids:
                        self.log(f"⚠️ Incomplete generation for '{json_file}'. Missing scenes: {missing_ids}")
                        incomplete_path = os.path.join(save_dir, "incomplete.txt")
                        with open(incomplete_path, "w", encoding="utf-8") as f:
                            f.write("missing=" + ",".join(map(str, missing_ids)))
                        self.log(f"📝 Wrote {os.path.basename(incomplete_path)}. Merge is skipped.")
                        continue
                    else:
                        with open(os.path.join(save_dir, "finish.txt"), "w", encoding="utf-8") as f:
                            f.write("done")
                        self.log("✅ All scenes present — finish.txt created, starting merge...")
                        current_mode = self.mode.get()
                        final_video = None
                        if current_mode == "Sound Relief":
                            final_video = self.create_sound_relief_video(save_dir, self.loop_duration.get())
                        elif current_mode == "Restorasi":
                            final_video = self.merge_with_intro(save_dir)
                        elif self.auto_merge_var.get():
                            final_video = self.merge_process(save_dir)
                        if final_video and self.upscale_var.get():
                            upscaled = final_video.replace(".mp4", "_4K.mp4")
                            if self.upscale_video(final_video, upscaled):
                                final_video = upscaled
                        if final_video and self.upload_youtube_var.get():
                            video_title = f"{os.path.splitext(json_file)[0]} - {current_mode}"
                            self.upload_to_youtube(final_video, video_title, current_mode)
                self.log("🎉 ALL JSON FILES PROCESSED!")
        finally:
            if context is not None:
                try:
                    context.close()
                except Exception:
                    pass
            self.is_running = False
            wx.CallAfter(self._cleanup_complete)

    # =========================
    # FLOW AUTOMATION (no sidepanel injection)
    # =========================
    def run_automator_logic_flow(self):
        self.is_running = True
        self.start_btn.Disable()
        self.pause_btn.Enable()
        self.stop_btn.Enable()
        from flow_editor_runner import FlowEditorRunner  # local import to avoid optional dependency at load
        runner = None
        try:
            for json_file in sorted(os.listdir(self.prompt_folder.get())):
                if not self.is_running:
                    self.log("⏹ Automation stopped by user")
                    break
                if not json_file.endswith(".json"):
                    continue
                save_dir = os.path.join(self.base_download_path, os.path.splitext(json_file)[0])
                os.makedirs(save_dir, exist_ok=True)
                with open(os.path.join(self.prompt_folder.get(), json_file), 'r', encoding='utf-8') as f:
                    data_json = json.load(f)
                total_scenes = len(data_json)
                self.log("=" * 50)
                self.log(f"📁 Processing (Flow): {json_file} (total scenes: {total_scenes})")
                self.log(f"🧭 Generation Method: {self.gen_method.get()}")
                if self.seed_image_path.get():
                    self.log(f"🖼️ Seed Image: {self.seed_image_path.get()}")
                processed_scenes = self.check_processed_videos(save_dir, total_scenes)
                if processed_scenes:
                    self.log(f"⏭️ Skipping {len(processed_scenes)} already processed scenes")
                # Start Flow runner for this JSON
                flow_ext_root = os.getenv("FLOW_EXTENSIONS_ROOT", os.path.abspath("Extensions"))
                flow_user_data = os.getenv("FLOW_USER_DATA_DIR", os.path.abspath("UserDataFlow"))
                flow_headless  = os.getenv("FLOW_HEADLESS", "False").lower() in ("1", "true", "yes")
                flow_acc_start = int(os.getenv("FLOW_ACCOUNT_START", str(self.flow_account_start.get())))
                runner = FlowEditorRunner(
                    email=self.email,
                    password=self.pwd,
                    extensions_root=flow_ext_root,
                    user_data_dir=flow_user_data,
                    download_dir=save_dir,
                    headless=flow_headless,
                    start_account_index=flow_acc_start,
                    timeout_ms=self.timeout.get() * 1000,
                    preferred_ext_id=os.getenv("FLOW_EXT_ID"),
                    keep_popup_open=True,
                    log_fn=self.log,
                )
                context = runner.start_context()
                popup   = runner.open_extension_popup()
                runner.handle_login_prompt_if_any()
                dashboard = runner.launch_flow_dashboard(runner.account_idx)
                runner.open_project_and_wait_editor()
                vertical = True if self.mode.get() == "Shorts" else False
                runner.apply_one_time_settings(vertical=vertical)
                last_frame_path = None
                for i, item in enumerate(data_json, 1):
                    while self.is_paused and self.is_running:
                        time.sleep(1)
                    if not self.is_running:
                        break
                    if i in processed_scenes:
                        self.log(f"⏭️ Scene #{i} already exists, skipping...")
                        video_path_existing = os.path.join(save_dir, f"{i}.mp4")
                        if os.path.exists(video_path_existing):
                            temp_frame = os.path.join(save_dir, f"last_frame_{i}.jpg")
                            subprocess.run([self.ffmpeg_path, '-sseof', '-1', '-i', video_path_existing,
                                            '-update', '1', '-q:v', '2', '-frames:v', '1',
                                            temp_frame, '-y'],
                                           stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
                            last_frame_path = temp_frame
                        continue
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
                    guide_image = None
                    if last_frame_path and os.path.exists(last_frame_path) and i > 1:
                        guide_image = last_frame_path
                    elif i == 1 and self.seed_image_path.get():
                        guide_image = self.seed_image_path.get()
                    self.log(f"🎬 Scene #{i}: Flow generating...")
                    result_path = runner.generate_scene(
                        scene_index=i,
                        prompt_text=prompt_text,
                        guide_image=guide_image,
                        save_dir=save_dir,
                        max_retries=3,
                    )
                    if not result_path or not os.path.exists(result_path):
                        self.log("🔁 Scene failed after 3 tries — rotating account & retrying...")
                        runner.rotate_account_and_reopen_editor()
                        runner.apply_one_time_settings(vertical=vertical)
                        result_path = runner.generate_scene(
                            scene_index=i,
                            prompt_text=prompt_text,
                            guide_image=guide_image,
                            save_dir=save_dir,
                            max_retries=3,
                        )
                    if result_path and os.path.exists(result_path):
                        temp_frame = os.path.join(save_dir, f"last_frame_{i}.jpg")
                        subprocess.run([self.ffmpeg_path, '-sseof', '-1', '-i', result_path,
                                        '-update', '1', '-q:v', '2', '-frames:v', '1',
                                        temp_frame, '-y'],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
                        last_frame_path = temp_frame
                        self.log(f"✅ Scene #{i}: Flow SUCCESS")
                    else:
                        self.log(f"❌ Scene #{i}: Flow FAILED after rotation")
                generated_ids, missing_ids = self.compute_generation_status(save_dir, total_scenes)
                if missing_ids:
                    self.log(f"⚠️ Incomplete generation for '{json_file}'. Missing scenes: {missing_ids}")
                    incomplete_path = os.path.join(save_dir, "incomplete.txt")
                    with open(incomplete_path, "w", encoding="utf-8") as f:
                        f.write("missing=" + ",".join(map(str, missing_ids)))
                    self.log(f"📝 Wrote {os.path.basename(incomplete_path)}. Merge is skipped.")
                    runner.close()
                    runner = None
                    continue
                else:
                    with open(os.path.join(save_dir, "finish.txt"), "w", encoding="utf-8") as f:
                        f.write("done")
                    self.log("✅ All scenes present — finish.txt created, starting merge...")
                    current_mode = self.mode.get()
                    final_video = None
                    if current_mode == "Sound Relief":
                        final_video = self.create_sound_relief_video(save_dir, self.loop_duration.get())
                    elif current_mode == "Restorasi":
                        final_video = self.merge_with_intro(save_dir)
                    elif self.auto_merge_var.get():
                        final_video = self.merge_process(save_dir)
                    if final_video and self.upscale_var.get():
                        upscaled = final_video.replace(".mp4", "_4K.mp4")
                        if self.upscale_video(final_video, upscaled):
                            final_video = upscaled
                    if final_video and self.upload_youtube_var.get():
                        video_title = f"{os.path.splitext(json_file)[0]} - {current_mode}"
                        self.upload_to_youtube(final_video, video_title, current_mode)
                if runner:
                    runner.close()
                    runner = None
            self.log("🎉 ALL JSON FILES PROCESSED (Flow)!")
        finally:
            if runner:
                runner.close()
            self.is_running = False
            wx.CallAfter(self._cleanup_complete)

    # =========================
    # GOOGLE FLOW AUTOMATION
    # =========================
    def run_automator_logic_google_flow(self):
        """Google Flow Ultra automation with credential login and session management"""
        self.is_running = True
        self.start_btn.Disable()
        self.pause_btn.Enable()
        self.stop_btn.Enable()
        
        google_flow_url = "https://labs.google/fx/id/tools/flow"
        google_flow_user_data = os.path.abspath("UserDataGoogleFlow")
        context = None
        
        try:
            with sync_playwright() as p:
                self.log("🌐 Starting Google Flow Browser...")
                os.makedirs(google_flow_user_data, exist_ok=True)
                
                context = p.chromium.launch_persistent_context(
                    user_data_dir=google_flow_user_data,
                    headless=False,
                    viewport={"width": 1920, "height": 1080},
                    accept_downloads=True,
                )
                context.set_default_timeout(self.timeout.get() * 1000)
                page = context.new_page()
                
                self.log("➡️ Navigating to Google Flow Ultra...")
                page.goto(google_flow_url, wait_until="domcontentloaded")
                time.sleep(3)
                
                # Check if login is needed
                username = self.google_flow_username.get()
                password = self.google_flow_password.get()
                
                if not username or not password:
                    self.log("⚠️ Google Flow credentials not set. Please configure username and password.")
                    messagebox.showwarning("Warning", "Please set Google Flow username and password in the credentials section.")
                    return
                
                # Attempt to detect and handle login
                try:
                    # This is a placeholder - actual selectors will depend on Google Flow's login page
                    # Check if we need to login by looking for common login elements
                    self.log("🔐 Checking if login is required...")
                    
                    # Try to find login fields (adjust selectors based on actual Google Flow login page)
                    if page.locator('input[type="email"], input[type="text"][name*="user"], input[name*="email"]').first.is_visible(timeout=5000):
                        self.log("🔐 Login form detected, filling credentials...")
                        
                        # Fill username/email
                        email_field = page.locator('input[type="email"], input[type="text"][name*="user"], input[name*="email"]').first
                        email_field.fill(username)
                        page.keyboard.press("Enter")
                        time.sleep(2)
                        
                        # Fill password
                        if page.locator('input[type="password"]').first.is_visible(timeout=10000):
                            password_field = page.locator('input[type="password"]').first
                            password_field.fill(password)
                            page.keyboard.press("Enter")
                            time.sleep(3)
                            
                        self.log("✅ Login credentials submitted")
                    else:
                        self.log("✅ Already logged in (session exists)")
                except Exception as e:
                    self.log(f"ℹ️ Login check skipped or session already active: {str(e)[:100]}")
                
                # Wait for the main Flow interface to load
                self.log("⏳ Waiting for Google Flow interface to load...")
                time.sleep(5)
                
                # Look for "Project Baru" or "New Project" button
                try:
                    # Adjust selector based on actual Google Flow UI
                    new_project_btn = page.locator("button:has-text('Project Baru'), button:has-text('New Project'), button:has-text('Create')").first
                    if new_project_btn.is_visible(timeout=10000):
                        self.log("🆕 Clicking 'Project Baru' button...")
                        new_project_btn.click()
                        time.sleep(3)
                        self.log("✅ New project created, ready to start Flow automation")
                    else:
                        self.log("⚠️ 'Project Baru' button not found, continuing with current state")
                except Exception as e:
                    self.log(f"⚠️ Could not click new project: {str(e)[:100]}")
                
                # Now run the same Flow logic as in run_automator_logic_flow
                from flow_editor_runner import FlowEditorRunner
                runner = None
                
                for json_file in sorted(os.listdir(self.prompt_folder.get())):
                    if not self.is_running:
                        self.log("⏹ Automation stopped by user")
                        break
                    if not json_file.endswith(".json"):
                        continue
                    
                    save_dir = os.path.join(self.base_download_path, os.path.splitext(json_file)[0])
                    os.makedirs(save_dir, exist_ok=True)
                    
                    with open(os.path.join(self.prompt_folder.get(), json_file), 'r', encoding='utf-8') as f:
                        data_json = json.load(f)
                    
                    total_scenes = len(data_json)
                    self.log("=" * 50)
                    self.log(f"📁 Processing (Google Flow): {json_file} (total scenes: {total_scenes})")
                    
                    processed_scenes = self.check_processed_videos(save_dir, total_scenes)
                    if processed_scenes:
                        self.log(f"⏭️ Skipping {len(processed_scenes)} already processed scenes")
                    
                    # Use the existing context/page instead of creating new one
                    # Process each scene with Google Flow interface
                    last_frame_path = None
                    for i, item in enumerate(data_json, 1):
                        while self.is_paused and self.is_running:
                            time.sleep(1)
                        if not self.is_running:
                            break
                        
                        if i in processed_scenes:
                            self.log(f"⏭️ Scene #{i} already exists, skipping...")
                            continue
                        
                        # Extract prompt
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
                        
                        self.log(f"🎬 Scene #{i}: Processing with Google Flow...")
                        # Here you would interact with the Google Flow UI to generate the video
                        # This is a placeholder - actual implementation depends on Google Flow's interface
                        self.log(f"✍️ Prompt: {prompt_text[:100]}...")
                        
                        # TODO: Implement actual Google Flow video generation interaction
                        # This would involve finding the prompt input, submitting, waiting for generation, downloading
                        
                    # Merge logic (same as Flow)
                    generated_ids, missing_ids = self.compute_generation_status(save_dir, total_scenes)
                    if missing_ids:
                        self.log(f"⚠️ Incomplete generation for '{json_file}'. Missing scenes: {missing_ids}")
                        incomplete_path = os.path.join(save_dir, "incomplete.txt")
                        with open(incomplete_path, "w", encoding="utf-8") as f:
                            f.write("missing=" + ",".join(map(str, missing_ids)))
                        self.log(f"📝 Wrote {os.path.basename(incomplete_path)}. Merge is skipped.")
                        continue
                    else:
                        with open(os.path.join(save_dir, "finish.txt"), "w", encoding="utf-8") as f:
                            f.write("done")
                        self.log("✅ All scenes present — finish.txt created, starting merge...")
                        
                        current_mode = self.mode.get()
                        final_video = None
                        if current_mode == "Sound Relief":
                            final_video = self.create_sound_relief_video(save_dir, self.loop_duration.get())
                        elif current_mode == "Restorasi":
                            final_video = self.merge_with_intro(save_dir)
                        elif self.auto_merge_var.get():
                            final_video = self.merge_process(save_dir)
                        
                        if final_video and self.upscale_var.get():
                            upscaled = final_video.replace(".mp4", "_4K.mp4")
                            if self.upscale_video(final_video, upscaled):
                                final_video = upscaled
                
                self.log("🎉 ALL JSON FILES PROCESSED (Google Flow)!")
        
        finally:
            if context is not None:
                try:
                    context.close()
                except Exception:
                    pass
            self.is_running = False
            wx.CallAfter(self._cleanup_complete)

    def start_automation_thread(self): 
        # Validasi seperti biasa 
        if not self.prompt_folder.get(): 
            messagebox.showwarning("Warning", "Silahkan pilih folder JSON prompt terlebih dahulu!") 
            return 
        if not self.base_download_path: 
            messagebox.showwarning("Warning", "DOWNLOAD_PATH tidak ditemukan di .env file!") 
            return 
        if self.is_running: 
            messagebox.showinfo("Info", "Automation sudah berjalan!") 
            return 
        if self.mode.get() == "Restorasi": 
            intro_path = os.path.join(self.assets_folder, "intro.mp4") 
            if not os.path.exists(intro_path): 
                response = messagebox.askyesno( 
                    "Warning", 
                    "intro.mp4 tidak ditemukan di folder Assets.\nLanjutkan tanpa intro?" 
                ) 
                if not response: 
                    return 
        if self.mode.get() == "Sound Relief": 
            if not os.path.exists(self.music_folder): 
                messagebox.showwarning( 
                    "Warning", 
                    f"Folder musik tidak ditemukan: {self.music_folder}\nSound Relief membutuhkan file musik MP3!" 
                ) 
                return 
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
            if not os.path.exists(self.client_secrets): 
                messagebox.showwarning( 
                    "Warning", 
                    f"YouTube client_secrets.json tidak ditemukan!\nPath: {self.client_secrets}" 
                ) 
                return 
        # Validate Google Flow credentials if using Google Flow subcategory 
        if self.video_gen_subcategory.get() == "Google Flow": 
            if not self.google_flow_username.get() or not self.google_flow_password.get(): 
                messagebox.showwarning( 
                    "Warning", 
                    "Google Flow credentials are required!\nPlease set username and password for Google Flow." 
                ) 
                return 
        # Logging awal 
        self.log("=" * 50) 
        self.log("🚀 STARTING AUTOMATION...") 
        self.log(f"📂 Prompt Folder: {self.prompt_folder.get()}") 
        self.log(f"🎯 Mode: {self.mode.get()}") 
        self.log(f"🎬 Generator: {self.generator.get()}") 
        self.log(f"⏱️ Timeout: {self.timeout.get()}s") 
        self.log(f"🔗 Auto Merge: {'Yes' if self.auto_merge_var.get() else 'No'}") 
        self.log(f"🔍 Upscale 4K: {'Yes' if self.upscale_var.get() else 'No'}") 
        self.log(f"🧭 Video Generator Type: {self.video_gen_subcategory.get()}") 
        if self.seed_image_path.get(): 
            self.log(f"🖼️ Seed Image: {self.seed_image_path.get()}") 
        if self.video_gen_subcategory.get() == "Google Flow": 
            self.log(f"🔐 Google Flow User: {self.google_flow_username.get()}") 
        if self.mode.get() == "Sound Relief": 
            self.log(f"🎵 Loop Duration: {self.loop_duration.get()} minutes") 
            self.log(f"🎶 Music Folder: {self.music_folder}") 
        self.log("=" * 50) 
        # Jalankan thread sesuai metode 
        subcategory = self.video_gen_subcategory.get() 
        if subcategory == "Google Flow": 
            self.pipeline_thread = threading.Thread(target=self.run_automator_logic_google_flow, daemon=True)
            self.pipeline_thread.start() 
        elif subcategory == "Flow Video Generator": 
            self.pipeline_thread = threading.Thread(target=self.run_automator_logic_flow, daemon=True)
            self.pipeline_thread.start() 
        else: 
            # Default or Nexa
            self.pipeline_thread = threading.Thread(target=self.run_automator_logic, daemon=True)
            self.pipeline_thread.start() 

# ========================= 
# Entry point 
# ========================= 
if __name__ == "__main__": 
    app = wx.App(False) 
    frame = NexabotApp() 
    frame.Show() 
    app.MainLoop() 
