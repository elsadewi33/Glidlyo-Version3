"""Video Uploader tab with YouTube channel mapping and other platforms."""
import os
import json
import wx
from ui.dialogs import filedialog, messagebox


class VideoUploaderTab(wx.Panel):
    """Video Uploader tab containing sub-tabs for different platforms."""
    
    def __init__(self, parent, app_state):
        """Initialize the Video Uploader tab.
        
        Args:
            parent: Parent window
            app_state: Dictionary containing shared application state and variables
        """
        super().__init__(parent)
        self.app_state = app_state
        
        # Create notebook for sub-tabs
        self.notebook = wx.Notebook(self)
        
        # Create sub-tabs
        self.youtube_tab = YouTubeUploaderPanel(self.notebook, app_state)
        self.facebook_tab = PlaceholderPanel(self.notebook, "Facebook")
        self.tiktok_tab = PlaceholderPanel(self.notebook, "TikTok")
        self.instagram_tab = PlaceholderPanel(self.notebook, "Instagram")
        
        # Add tabs to notebook
        self.notebook.AddPage(self.youtube_tab, "YouTube")
        self.notebook.AddPage(self.facebook_tab, "Facebook")
        self.notebook.AddPage(self.tiktok_tab, "TikTok")
        self.notebook.AddPage(self.instagram_tab, "Instagram")
        
        # Layout
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 5)
        self.SetSizer(sizer)


class YouTubeUploaderPanel(wx.Panel):
    """Panel for YouTube upload configuration and channel mapping."""
    
    def __init__(self, parent, app_state):
        """Initialize YouTube uploader panel."""
        super().__init__(parent)
        self.app_state = app_state
        
        # Get youtube_channels from app_state
        self.youtube_channels = app_state.get('youtube_channels', {
            "Shorts": {"name": "", "credentials": ""},
            "Sound Relief": {"name": "", "credentials": ""},
            "Restorasi": {"name": "", "credentials": ""},
            "Home Renovation": {"name": "", "credentials": ""}
        })
        
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Title
        title = wx.StaticText(self, label="YouTube Channel Mapping")
        title_font = wx.Font(12, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        title.SetFont(title_font)
        main_sizer.Add(title, 0, wx.ALL, 10)
        
        # Info
        info_text = wx.StaticText(self, label="Configure YouTube channel and credentials for each video mode.")
        info_text.SetForegroundColour(wx.Colour(128, 128, 128))
        main_sizer.Add(info_text, 0, wx.ALL, 10)
        
        # Channel mapping
        mapping_box = wx.StaticBox(self, label="Channel Mapping per Mode")
        mapping_sizer = wx.StaticBoxSizer(mapping_box, wx.VERTICAL)
        
        # Create grid for channel mappings
        grid = wx.FlexGridSizer(rows=5, cols=4, vgap=10, hgap=10)
        
        # Headers
        grid.Add(wx.StaticText(mapping_box, label="Mode"), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT)
        grid.Add(wx.StaticText(mapping_box, label="Channel Name"), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT)
        grid.Add(wx.StaticText(mapping_box, label="Credentials File"), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT)
        grid.Add(wx.StaticText(mapping_box, label=""), 0)  # Button column
        
        # Storage for controls
        self.name_ctrls = {}
        self.cred_labels = {}
        
        # Create rows for each mode
        modes = ["Shorts", "Sound Relief", "Restorasi", "Home Renovation"]
        for mode in modes:
            # Mode label
            mode_label = wx.StaticText(mapping_box, label=mode)
            mode_label_font = wx.Font(10, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
            mode_label.SetFont(mode_label_font)
            grid.Add(mode_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT)
            
            # Channel name text control
            name_ctrl = wx.TextCtrl(mapping_box, value=self.youtube_channels.get(mode, {}).get("name", ""))
            name_ctrl.SetMinSize((200, -1))
            self.name_ctrls[mode] = name_ctrl
            grid.Add(name_ctrl, 1, wx.EXPAND)
            
            # Credentials file label
            cred_file = self.youtube_channels.get(mode, {}).get("credentials", "")
            cred_label = wx.StaticText(mapping_box, label=os.path.basename(cred_file) if cred_file else "Not set")
            cred_label.SetForegroundColour(wx.Colour(0, 0, 255))
            cred_label.SetMinSize((200, -1))
            self.cred_labels[mode] = cred_label
            grid.Add(cred_label, 1, wx.EXPAND)
            
            # Browse button
            browse_btn = wx.Button(mapping_box, label="Browse...")
            browse_btn.Bind(wx.EVT_BUTTON, lambda e, m=mode: self.on_browse_credentials(m))
            grid.Add(browse_btn, 0, wx.ALIGN_CENTER_VERTICAL)
        
        grid.AddGrowableCol(1, 1)
        grid.AddGrowableCol(2, 1)
        mapping_sizer.Add(grid, 0, wx.EXPAND | wx.ALL, 10)
        
        main_sizer.Add(mapping_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        # Save button
        save_btn = wx.Button(self, label="💾 Save Channel Settings")
        save_btn.SetBackgroundColour(wx.Colour(40, 167, 69))
        save_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        save_btn.Bind(wx.EVT_BUTTON, self.on_save)
        main_sizer.Add(save_btn, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        
        # Status
        self.status_label = wx.StaticText(self, label="")
        self.status_label.SetForegroundColour(wx.Colour(0, 128, 0))
        main_sizer.Add(self.status_label, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        
        # Help text
        help_text = wx.StaticText(self, label="Note: Credentials file is the token.json file for each YouTube channel.\nMake sure each channel has its own credentials file.")
        help_text.SetForegroundColour(wx.Colour(128, 128, 128))
        main_sizer.Add(help_text, 0, wx.ALL, 10)
        
        self.SetSizer(main_sizer)
    
    def on_browse_credentials(self, mode):
        """Handle browse credentials button click."""
        path = filedialog.askopenfilename(
            title=f"Select Credentials File for {mode}",
            filetypes=(("JSON files", "*.json"), ("All files", "*.*"))
        )
        if path:
            self.youtube_channels[mode]["credentials"] = os.path.normpath(path)
            self.cred_labels[mode].SetLabel(os.path.basename(path))
            self.cred_labels[mode].SetToolTip(wx.ToolTip(path))
            self.Layout()
    
    def on_save(self, event):
        """Handle save button click."""
        # Update channel names from text controls
        for mode, ctrl in self.name_ctrls.items():
            if mode not in self.youtube_channels:
                self.youtube_channels[mode] = {}
            self.youtube_channels[mode]["name"] = ctrl.GetValue()
        
        # Save to file
        config_file = "youtube_channels.json"
        try:
            with open(config_file, 'w') as f:
                json.dump(self.youtube_channels, f, indent=2)
            
            self.status_label.SetLabel("✅ Settings saved successfully!")
            
            # Update app_state
            self.app_state['youtube_channels'] = self.youtube_channels
            
            # Log if callback available
            if 'log_callback' in self.app_state and self.app_state['log_callback']:
                self.app_state['log_callback']("💾 YouTube channel settings saved to youtube_channels.json")
            
            messagebox.showinfo("Success", f"YouTube channel settings saved to {config_file}!")
        
        except Exception as e:
            self.status_label.SetLabel("❌ Failed to save settings")
            messagebox.showerror("Error", f"Failed to save settings:\n{str(e)}")


class PlaceholderPanel(wx.Panel):
    """Placeholder panel for platforms coming soon."""
    
    def __init__(self, parent, platform_name):
        """Initialize placeholder panel.
        
        Args:
            parent: Parent window
            platform_name: Name of the platform (e.g., "Facebook", "TikTok")
        """
        super().__init__(parent)
        
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Title
        title = wx.StaticText(self, label=f"{platform_name} Uploader")
        title_font = wx.Font(12, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        title.SetFont(title_font)
        main_sizer.Add(title, 0, wx.ALL, 10)
        
        # Coming soon message
        coming_soon = wx.StaticText(self, label="🚧 Coming Soon 🚧")
        coming_soon_font = wx.Font(16, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        coming_soon.SetFont(coming_soon_font)
        coming_soon.SetForegroundColour(wx.Colour(255, 165, 0))
        main_sizer.Add(coming_soon, 0, wx.ALIGN_CENTER | wx.ALL, 20)
        
        info_text = wx.StaticText(self, label=f"{platform_name} upload functionality will be added in a future update.\nStay tuned!")
        info_text.SetForegroundColour(wx.Colour(128, 128, 128))
        main_sizer.Add(info_text, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        
        self.SetSizer(main_sizer)
