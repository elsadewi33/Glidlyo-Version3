"""Video Generator tab with sub-tabs for Default, Nexa, Flow, and Google Flow."""
import os
import wx
from ui.variables import SimpleVar
from ui.dialogs import filedialog


class VideoGeneratorTab(wx.Panel):
    """Video Generator tab containing sub-tabs for different generation methods."""
    
    def __init__(self, parent, app_state):
        """Initialize the Video Generator tab.
        
        Args:
            parent: Parent window
            app_state: Dictionary containing shared application state and variables
        """
        super().__init__(parent)
        self.app_state = app_state
        
        # Create notebook for sub-tabs
        self.notebook = wx.Notebook(self)
        
        # Create sub-tabs
        self.default_tab = DefaultGeneratorPanel(self.notebook, app_state)
        self.nexa_tab = NexaGeneratorPanel(self.notebook, app_state)
        self.flow_tab = FlowGeneratorPanel(self.notebook, app_state)
        self.google_flow_tab = GoogleFlowGeneratorPanel(self.notebook, app_state)
        
        # Add tabs to notebook
        self.notebook.AddPage(self.default_tab, "Default")
        self.notebook.AddPage(self.nexa_tab, "Nexa")
        self.notebook.AddPage(self.flow_tab, "Flow Video Generator")
        self.notebook.AddPage(self.google_flow_tab, "Google Flow")
        
        # Layout
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 5)
        self.SetSizer(sizer)
        
        # Bind tab change event to update app state
        self.notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.on_tab_changed)
    
    def on_tab_changed(self, event):
        """Handle tab change event."""
        page_idx = event.GetSelection()
        tab_names = ["Default", "Nexa", "Flow Video Generator", "Google Flow"]
        if page_idx < len(tab_names):
            self.app_state['video_gen_subcategory'].set(tab_names[page_idx])
        event.Skip()


class DefaultGeneratorPanel(wx.Panel):
    """Default generator panel with full features including extensions."""
    
    def __init__(self, parent, app_state):
        """Initialize Default generator panel."""
        super().__init__(parent)
        self.app_state = app_state
        
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Title
        title = wx.StaticText(self, label="Default Video Generator")
        title_font = wx.Font(12, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        title.SetFont(title_font)
        main_sizer.Add(title, 0, wx.ALL, 10)
        
        # Path Settings
        path_box = wx.StaticBox(self, label="Path Settings")
        path_sizer = wx.StaticBoxSizer(path_box, wx.VERTICAL)
        
        btn_select_prompt = wx.Button(path_box, label="Select JSON Prompt Folder")
        btn_select_prompt.Bind(wx.EVT_BUTTON, self.on_select_prompt)
        path_sizer.Add(btn_select_prompt, 0, wx.EXPAND | wx.ALL, 5)
        
        self.prompt_folder_label = wx.StaticText(path_box, label="No folder selected")
        self.prompt_folder_label.SetForegroundColour(wx.Colour(0, 0, 255))
        path_sizer.Add(self.prompt_folder_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        
        main_sizer.Add(path_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        # Mode Selection
        mode_box = wx.StaticBox(self, label="Mode Selection")
        mode_sizer = wx.StaticBoxSizer(mode_box, wx.HORIZONTAL)
        
        modes = ["Shorts", "Sound Relief", "Restorasi", "Home Renovation"]
        lbl_mode = wx.StaticText(mode_box, label="Select Mode:")
        self.mode_combo = wx.ComboBox(mode_box, choices=modes, style=wx.CB_READONLY, size=(200, -1))
        self.mode_combo.SetValue(self.app_state['mode'].get())
        self.mode_combo.Bind(wx.EVT_COMBOBOX, self.on_mode_changed)
        
        mode_sizer.Add(lbl_mode, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        mode_sizer.Add(self.mode_combo, 1, wx.ALL | wx.EXPAND, 5)
        
        main_sizer.Add(mode_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        # Sound Relief Options (conditionally shown)
        self.sound_relief_panel = self._create_sound_relief_panel()
        main_sizer.Add(self.sound_relief_panel, 0, wx.EXPAND | wx.ALL, 5)
        self.sound_relief_panel.Hide()
        
        # Configurations
        config_box = wx.StaticBox(self, label="Configurations")
        config_sizer = wx.StaticBoxSizer(config_box, wx.VERTICAL)
        
        grid_cfg = wx.FlexGridSizer(rows=6, cols=2, vgap=5, hgap=10)
        
        # Generator
        grid_cfg.Add(wx.StaticText(config_box, label="Generator:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.generator_combo = wx.ComboBox(config_box, choices=["Veo 3.1", "Nexa Gen", "Sora 2"], style=wx.CB_READONLY)
        self.generator_combo.SetValue(self.app_state['generator'].get())
        self.generator_combo.Bind(wx.EVT_COMBOBOX, lambda e: self.app_state['generator'].set(self.generator_combo.GetValue()))
        grid_cfg.Add(self.generator_combo, 1, wx.EXPAND)
        
        # Timeout
        grid_cfg.Add(wx.StaticText(config_box, label="Timeout (sec):"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.timeout_spin = wx.SpinCtrl(config_box, min=10, max=36000, initial=self.app_state['timeout'].get())
        self.timeout_spin.Bind(wx.EVT_SPINCTRL, lambda e: self.app_state['timeout'].set(self.timeout_spin.GetValue()))
        grid_cfg.Add(self.timeout_spin, 1, wx.EXPAND)
        
        # Auto Merge
        self.auto_merge_cb = wx.CheckBox(config_box, label="Auto Merge Video")
        self.auto_merge_cb.SetValue(self.app_state['auto_merge_var'].get())
        self.auto_merge_cb.Bind(wx.EVT_CHECKBOX, lambda e: self.app_state['auto_merge_var'].set(self.auto_merge_cb.GetValue()))
        grid_cfg.Add(self.auto_merge_cb, 0, wx.ALIGN_LEFT)
        grid_cfg.AddSpacer(0)
        
        # Upscale
        self.upscale_cb = wx.CheckBox(config_box, label="Upscale to 4K")
        self.upscale_cb.SetValue(self.app_state['upscale_var'].get())
        self.upscale_cb.Bind(wx.EVT_CHECKBOX, lambda e: self.app_state['upscale_var'].set(self.upscale_cb.GetValue()))
        grid_cfg.Add(self.upscale_cb, 0, wx.ALIGN_LEFT)
        grid_cfg.AddSpacer(0)
        
        # Generation Method
        grid_cfg.Add(wx.StaticText(config_box, label="Generation Method:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.gen_method_combo = wx.ComboBox(config_box, choices=["Default", "Flow"], style=wx.CB_READONLY)
        self.gen_method_combo.SetValue(self.app_state['gen_method'].get())
        self.gen_method_combo.Bind(wx.EVT_COMBOBOX, lambda e: self.app_state['gen_method'].set(self.gen_method_combo.GetValue()))
        grid_cfg.Add(self.gen_method_combo, 1, wx.EXPAND)
        
        # Seed Image
        btn_seed = wx.Button(config_box, label="Select Seed Image (Optional)")
        btn_seed.Bind(wx.EVT_BUTTON, self.on_select_seed_image)
        grid_cfg.Add(btn_seed, 0, wx.ALIGN_LEFT)
        self.seed_image_label = wx.StaticText(config_box, label="No seed image")
        grid_cfg.Add(self.seed_image_label, 1, wx.EXPAND)
        
        grid_cfg.AddGrowableCol(1, 1)
        config_sizer.Add(grid_cfg, 0, wx.EXPAND | wx.ALL, 5)
        
        main_sizer.Add(config_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        # Info
        info_text = wx.StaticText(self, label="Default mode uses Playwright with Nexabot extensions for captcha solving.")
        info_text.SetForegroundColour(wx.Colour(128, 128, 128))
        main_sizer.Add(info_text, 0, wx.ALL, 10)
        
        self.SetSizer(main_sizer)
    
    def _create_sound_relief_panel(self):
        """Create Sound Relief options panel."""
        panel = wx.Panel(self)
        panel_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        lbl_loop = wx.StaticText(panel, label="Loop Duration (minutes):")
        self.loop_duration_ctrl = wx.SpinCtrl(panel, min=1, max=10000, initial=self.app_state['loop_duration'].get())
        self.loop_duration_ctrl.Bind(wx.EVT_SPINCTRL, lambda e: self.app_state['loop_duration'].set(self.loop_duration_ctrl.GetValue()))
        
        panel_sizer.Add(lbl_loop, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        panel_sizer.Add(self.loop_duration_ctrl, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        
        panel.SetSizer(panel_sizer)
        return panel
    
    def on_select_prompt(self, event):
        """Handle prompt folder selection."""
        path = filedialog.askdirectory("Select JSON Prompt Folder")
        if path:
            self.app_state['prompt_folder'].set(os.path.normpath(path))
            self.prompt_folder_label.SetLabel(self.app_state['prompt_folder'].get())
            self.Layout()
    
    def on_select_seed_image(self, event):
        """Handle seed image selection."""
        path = filedialog.askopenfilename(
            title="Select Seed Image",
            filetypes=(("Images", "*.png;*.jpg;*.jpeg;*.webp;*.heic;*.avif"), ("All files", "*.*"))
        )
        if path:
            self.app_state['seed_image_path'].set(os.path.normpath(path))
            self.seed_image_label.SetLabel(os.path.basename(self.app_state['seed_image_path'].get()))
    
    def on_mode_changed(self, event):
        """Handle mode selection change."""
        mode = self.mode_combo.GetValue()
        self.app_state['mode'].set(mode)
        
        # Show/hide Sound Relief options
        if mode == "Sound Relief":
            self.sound_relief_panel.Show()
        else:
            self.sound_relief_panel.Hide()
        self.Layout()


class NexaGeneratorPanel(wx.Panel):
    """Nexa generator panel (like Default but WITHOUT nexa_extension)."""
    
    def __init__(self, parent, app_state):
        """Initialize Nexa generator panel."""
        super().__init__(parent)
        self.app_state = app_state
        
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Title
        title = wx.StaticText(self, label="Nexa Video Generator")
        title_font = wx.Font(12, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        title.SetFont(title_font)
        main_sizer.Add(title, 0, wx.ALL, 10)
        
        # Info
        info_text = wx.StaticText(self, label="Nexa mode uses Playwright WITHOUT extensions (no captcha solver).\nUse this when captcha solving is not needed or causes issues.")
        info_text.SetForegroundColour(wx.Colour(128, 128, 128))
        main_sizer.Add(info_text, 0, wx.ALL, 10)
        
        # Path Settings (reuse from Default)
        path_box = wx.StaticBox(self, label="Path Settings")
        path_sizer = wx.StaticBoxSizer(path_box, wx.VERTICAL)
        
        btn_select_prompt = wx.Button(path_box, label="Select JSON Prompt Folder")
        btn_select_prompt.Bind(wx.EVT_BUTTON, self.on_select_prompt)
        path_sizer.Add(btn_select_prompt, 0, wx.EXPAND | wx.ALL, 5)
        
        self.prompt_folder_label = wx.StaticText(path_box, label="No folder selected")
        self.prompt_folder_label.SetForegroundColour(wx.Colour(0, 0, 255))
        path_sizer.Add(self.prompt_folder_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        
        main_sizer.Add(path_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        # Simplified config (just timeout and generator)
        config_box = wx.StaticBox(self, label="Configurations")
        config_sizer = wx.StaticBoxSizer(config_box, wx.VERTICAL)
        
        grid_cfg = wx.FlexGridSizer(rows=2, cols=2, vgap=5, hgap=10)
        
        grid_cfg.Add(wx.StaticText(config_box, label="Generator:"), 0, wx.ALIGN_CENTER_VERTICAL)
        generator_combo = wx.ComboBox(config_box, choices=["Veo 3.1", "Nexa Gen", "Sora 2"], style=wx.CB_READONLY)
        generator_combo.SetValue(self.app_state['generator'].get())
        generator_combo.Bind(wx.EVT_COMBOBOX, lambda e: self.app_state['generator'].set(generator_combo.GetValue()))
        grid_cfg.Add(generator_combo, 1, wx.EXPAND)
        
        grid_cfg.Add(wx.StaticText(config_box, label="Timeout (sec):"), 0, wx.ALIGN_CENTER_VERTICAL)
        timeout_spin = wx.SpinCtrl(config_box, min=10, max=36000, initial=self.app_state['timeout'].get())
        timeout_spin.Bind(wx.EVT_SPINCTRL, lambda e: self.app_state['timeout'].set(timeout_spin.GetValue()))
        grid_cfg.Add(timeout_spin, 1, wx.EXPAND)
        
        grid_cfg.AddGrowableCol(1, 1)
        config_sizer.Add(grid_cfg, 0, wx.EXPAND | wx.ALL, 5)
        
        main_sizer.Add(config_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        self.SetSizer(main_sizer)
    
    def on_select_prompt(self, event):
        """Handle prompt folder selection."""
        path = filedialog.askdirectory("Select JSON Prompt Folder")
        if path:
            self.app_state['prompt_folder'].set(os.path.normpath(path))
            self.prompt_folder_label.SetLabel(self.app_state['prompt_folder'].get())
            self.Layout()


class FlowGeneratorPanel(wx.Panel):
    """Flow Video Generator panel."""
    
    def __init__(self, parent, app_state):
        """Initialize Flow generator panel."""
        super().__init__(parent)
        self.app_state = app_state
        
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Title
        title = wx.StaticText(self, label="Flow Video Generator")
        title_font = wx.Font(12, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        title.SetFont(title_font)
        main_sizer.Add(title, 0, wx.ALL, 10)
        
        # Info
        info_text = wx.StaticText(self, label="Flow mode uses FlowEditorRunner for video generation.")
        info_text.SetForegroundColour(wx.Colour(128, 128, 128))
        main_sizer.Add(info_text, 0, wx.ALL, 10)
        
        # Path Settings
        path_box = wx.StaticBox(self, label="Path Settings")
        path_sizer = wx.StaticBoxSizer(path_box, wx.VERTICAL)
        
        btn_select_prompt = wx.Button(path_box, label="Select JSON Prompt Folder")
        btn_select_prompt.Bind(wx.EVT_BUTTON, self.on_select_prompt)
        path_sizer.Add(btn_select_prompt, 0, wx.EXPAND | wx.ALL, 5)
        
        self.prompt_folder_label = wx.StaticText(path_box, label="No folder selected")
        self.prompt_folder_label.SetForegroundColour(wx.Colour(0, 0, 255))
        path_sizer.Add(self.prompt_folder_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        
        main_sizer.Add(path_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        # Seed Image
        seed_box = wx.StaticBox(self, label="Seed Image (Optional)")
        seed_sizer = wx.StaticBoxSizer(seed_box, wx.VERTICAL)
        
        btn_seed = wx.Button(seed_box, label="Select Seed Image")
        btn_seed.Bind(wx.EVT_BUTTON, self.on_select_seed_image)
        seed_sizer.Add(btn_seed, 0, wx.ALL, 5)
        
        self.seed_image_label = wx.StaticText(seed_box, label="No seed image selected")
        seed_sizer.Add(self.seed_image_label, 0, wx.ALL, 5)
        
        main_sizer.Add(seed_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        self.SetSizer(main_sizer)
    
    def on_select_prompt(self, event):
        """Handle prompt folder selection."""
        path = filedialog.askdirectory("Select JSON Prompt Folder")
        if path:
            self.app_state['prompt_folder'].set(os.path.normpath(path))
            self.prompt_folder_label.SetLabel(self.app_state['prompt_folder'].get())
            self.Layout()
    
    def on_select_seed_image(self, event):
        """Handle seed image selection."""
        path = filedialog.askopenfilename(
            title="Select Seed Image",
            filetypes=(("Images", "*.png;*.jpg;*.jpeg;*.webp;*.heic;*.avif"), ("All files", "*.*"))
        )
        if path:
            self.app_state['seed_image_path'].set(os.path.normpath(path))
            self.seed_image_label.SetLabel(os.path.basename(self.app_state['seed_image_path'].get()))


class GoogleFlowGeneratorPanel(wx.Panel):
    """Google Flow generator panel with credentials."""
    
    def __init__(self, parent, app_state):
        """Initialize Google Flow generator panel."""
        super().__init__(parent)
        self.app_state = app_state
        
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Title
        title = wx.StaticText(self, label="Google Flow Video Generator")
        title_font = wx.Font(12, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        title.SetFont(title_font)
        main_sizer.Add(title, 0, wx.ALL, 10)
        
        # Info
        info_text = wx.StaticText(self, label="Google Flow mode uses Google Labs Flow for video generation.")
        info_text.SetForegroundColour(wx.Colour(128, 128, 128))
        main_sizer.Add(info_text, 0, wx.ALL, 10)
        
        # Path Settings
        path_box = wx.StaticBox(self, label="Path Settings")
        path_sizer = wx.StaticBoxSizer(path_box, wx.VERTICAL)
        
        btn_select_prompt = wx.Button(path_box, label="Select JSON Prompt Folder")
        btn_select_prompt.Bind(wx.EVT_BUTTON, self.on_select_prompt)
        path_sizer.Add(btn_select_prompt, 0, wx.EXPAND | wx.ALL, 5)
        
        self.prompt_folder_label = wx.StaticText(path_box, label="No folder selected")
        self.prompt_folder_label.SetForegroundColour(wx.Colour(0, 0, 255))
        path_sizer.Add(self.prompt_folder_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        
        main_sizer.Add(path_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        # Google Flow Credentials - FIXED: Use Panel instead of StaticBoxSizer.Show()
        self.cred_panel = wx.Panel(self)
        cred_sizer = wx.BoxSizer(wx.VERTICAL)
        
        cred_box = wx.StaticBox(self.cred_panel, label="Google Flow Credentials")
        cred_box_sizer = wx.StaticBoxSizer(cred_box, wx.VERTICAL)
        
        grid = wx.FlexGridSizer(rows=2, cols=2, vgap=5, hgap=10)
        
        grid.Add(wx.StaticText(cred_box, label="Username:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.user_ctrl = wx.TextCtrl(cred_box, value=self.app_state['google_flow_username'].get())
        self.user_ctrl.Bind(wx.EVT_TEXT, lambda e: self.app_state['google_flow_username'].set(self.user_ctrl.GetValue()))
        grid.Add(self.user_ctrl, 1, wx.EXPAND)
        
        grid.Add(wx.StaticText(cred_box, label="Password:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.pass_ctrl = wx.TextCtrl(cred_box, value=self.app_state['google_flow_password'].get(), style=wx.TE_PASSWORD)
        self.pass_ctrl.Bind(wx.EVT_TEXT, lambda e: self.app_state['google_flow_password'].set(self.pass_ctrl.GetValue()))
        grid.Add(self.pass_ctrl, 1, wx.EXPAND)
        
        grid.AddGrowableCol(1, 1)
        cred_box_sizer.Add(grid, 1, wx.EXPAND | wx.ALL, 5)
        
        cred_sizer.Add(cred_box_sizer, 1, wx.EXPAND)
        self.cred_panel.SetSizer(cred_sizer)
        
        main_sizer.Add(self.cred_panel, 0, wx.EXPAND | wx.ALL, 5)
        
        self.SetSizer(main_sizer)
    
    def on_select_prompt(self, event):
        """Handle prompt folder selection."""
        path = filedialog.askdirectory("Select JSON Prompt Folder")
        if path:
            self.app_state['prompt_folder'].set(os.path.normpath(path))
            self.prompt_folder_label.SetLabel(self.app_state['prompt_folder'].get())
            self.Layout()
