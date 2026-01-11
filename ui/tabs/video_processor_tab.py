"""Video Processor tab with Merge, Upscale, and Clipper functionality."""
import os
import wx
from ui.dialogs import filedialog, messagebox


class VideoProcessorTab(wx.Panel):
    """Video Processor tab containing sub-tabs for video processing operations."""
    
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
        self.upscale_tab = UpscalePanel(self.notebook, app_state)
        self.clipper_tab = ClipperPanel(self.notebook, app_state)
        
        # Add tabs to notebook
        self.notebook.AddPage(self.merge_tab, "Merge Video")
        self.notebook.AddPage(self.upscale_tab, "Upscale to 4K")
        self.notebook.AddPage(self.clipper_tab, "Clipper")
        
        # Layout
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 5)
        self.SetSizer(sizer)


class MergeVideoPanel(wx.Panel):
    """Panel for merging videos with optional intro."""
    
    def __init__(self, parent, app_state):
        """Initialize Merge Video panel."""
        super().__init__(parent)
        self.app_state = app_state
        
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Title
        title = wx.StaticText(self, label="Merge Videos")
        title_font = wx.Font(12, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        title.SetFont(title_font)
        main_sizer.Add(title, 0, wx.ALL, 10)
        
        # Info
        info_text = wx.StaticText(self, label="Merge numbered video files (1.mp4, 2.mp4, ...) into a single video.\nOptionally prepend an intro video.")
        info_text.SetForegroundColour(wx.Colour(128, 128, 128))
        main_sizer.Add(info_text, 0, wx.ALL, 10)
        
        # Input folder
        input_box = wx.StaticBox(self, label="Input Folder")
        input_sizer = wx.StaticBoxSizer(input_box, wx.VERTICAL)
        
        btn_select_folder = wx.Button(input_box, label="Select Folder with Numbered Videos")
        btn_select_folder.Bind(wx.EVT_BUTTON, self.on_select_folder)
        input_sizer.Add(btn_select_folder, 0, wx.EXPAND | wx.ALL, 5)
        
        self.folder_label = wx.StaticText(input_box, label="No folder selected")
        self.folder_label.SetForegroundColour(wx.Colour(0, 0, 255))
        input_sizer.Add(self.folder_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        
        main_sizer.Add(input_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        # Options
        options_box = wx.StaticBox(self, label="Options")
        options_sizer = wx.StaticBoxSizer(options_box, wx.VERTICAL)
        
        self.add_intro_cb = wx.CheckBox(options_box, label="Prepend Intro (from Assets/intro.mp4)")
        self.add_intro_cb.SetValue(False)
        options_sizer.Add(self.add_intro_cb, 0, wx.ALL, 5)
        
        self.reencode_cb = wx.CheckBox(options_box, label="Re-encode video (robust but slower)")
        self.reencode_cb.SetValue(True)  # Default to True for robust merging
        self.reencode_cb.SetToolTip(wx.ToolTip("Re-encoding ensures compatibility but takes longer. Use for fixing concat issues."))
        options_sizer.Add(self.reencode_cb, 0, wx.ALL, 5)
        
        main_sizer.Add(options_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        # Merge button
        self.merge_btn = wx.Button(self, label="Merge Videos")
        self.merge_btn.Bind(wx.EVT_BUTTON, self.on_merge)
        main_sizer.Add(self.merge_btn, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        
        # Status
        self.status_label = wx.StaticText(self, label="")
        self.status_label.SetForegroundColour(wx.Colour(0, 128, 0))
        main_sizer.Add(self.status_label, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        
        self.SetSizer(main_sizer)
        
        self.selected_folder = None
    
    def on_select_folder(self, event):
        """Handle folder selection."""
        path = filedialog.askdirectory("Select Folder with Numbered Videos")
        if path:
            self.selected_folder = os.path.normpath(path)
            self.folder_label.SetLabel(self.selected_folder)
            self.Layout()
    
    def on_merge(self, event):
        """Handle merge button click."""
        if not self.selected_folder:
            messagebox.showwarning("Warning", "Please select a folder first!")
            return
        
        # Import ffmpeg_ops here to avoid circular import
        from media.ffmpeg_ops import FFmpegOps
        from core.config import config
        from core.logger import Logger
        
        logger = Logger(log_callback=self.app_state.get('log_callback'))
        ffmpeg_ops = FFmpegOps(config, logger)
        
        try:
            self.status_label.SetLabel("Merging videos...")
            self.merge_btn.Disable()
            
            # Perform merge
            if self.add_intro_cb.GetValue():
                result = ffmpeg_ops.merge_with_intro(
                    self.selected_folder, 
                    reencode=self.reencode_cb.GetValue()
                )
            else:
                result = ffmpeg_ops.merge_videos(
                    self.selected_folder,
                    reencode=self.reencode_cb.GetValue()
                )
            
            if result:
                self.status_label.SetLabel(f"✅ Success: {os.path.basename(result)}")
                messagebox.showinfo("Success", f"Videos merged successfully!\n{result}")
            else:
                self.status_label.SetLabel("❌ Merge failed")
                messagebox.showerror("Error", "Failed to merge videos. Check the log for details.")
        
        except Exception as e:
            self.status_label.SetLabel("❌ Error occurred")
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
        
        finally:
            self.merge_btn.Enable()


class UpscalePanel(wx.Panel):
    """Panel for upscaling videos to 4K."""
    
    def __init__(self, parent, app_state):
        """Initialize Upscale panel."""
        super().__init__(parent)
        self.app_state = app_state
        
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Title
        title = wx.StaticText(self, label="Upscale Video to 4K")
        title_font = wx.Font(12, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        title.SetFont(title_font)
        main_sizer.Add(title, 0, wx.ALL, 10)
        
        # Info
        info_text = wx.StaticText(self, label="Upscale a video to 4K (3840x2160) resolution using FFmpeg.")
        info_text.SetForegroundColour(wx.Colour(128, 128, 128))
        main_sizer.Add(info_text, 0, wx.ALL, 10)
        
        # Input file
        input_box = wx.StaticBox(self, label="Input Video")
        input_sizer = wx.StaticBoxSizer(input_box, wx.VERTICAL)
        
        btn_select_file = wx.Button(input_box, label="Select Video File")
        btn_select_file.Bind(wx.EVT_BUTTON, self.on_select_file)
        input_sizer.Add(btn_select_file, 0, wx.EXPAND | wx.ALL, 5)
        
        self.file_label = wx.StaticText(input_box, label="No file selected")
        self.file_label.SetForegroundColour(wx.Colour(0, 0, 255))
        input_sizer.Add(self.file_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        
        main_sizer.Add(input_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        # Upscale button
        self.upscale_btn = wx.Button(self, label="Upscale to 4K")
        self.upscale_btn.Bind(wx.EVT_BUTTON, self.on_upscale)
        main_sizer.Add(self.upscale_btn, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        
        # Status
        self.status_label = wx.StaticText(self, label="")
        self.status_label.SetForegroundColour(wx.Colour(0, 128, 0))
        main_sizer.Add(self.status_label, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        
        self.SetSizer(main_sizer)
        
        self.selected_file = None
    
    def on_select_file(self, event):
        """Handle file selection."""
        path = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=(("Video files", "*.mp4;*.avi;*.mov;*.mkv"), ("All files", "*.*"))
        )
        if path:
            self.selected_file = os.path.normpath(path)
            self.file_label.SetLabel(os.path.basename(self.selected_file))
            self.Layout()
    
    def on_upscale(self, event):
        """Handle upscale button click."""
        if not self.selected_file:
            messagebox.showwarning("Warning", "Please select a video file first!")
            return
        
        # Import ffmpeg_ops here to avoid circular import
        from media.ffmpeg_ops import FFmpegOps
        from core.config import config
        from core.logger import Logger
        
        logger = Logger(log_callback=self.app_state.get('log_callback'))
        ffmpeg_ops = FFmpegOps(config, logger)
        
        try:
            self.status_label.SetLabel("Upscaling video... (this may take a while)")
            self.upscale_btn.Disable()
            
            # Create output path
            base, ext = os.path.splitext(self.selected_file)
            output_path = f"{base}_4K{ext}"
            
            # Perform upscale
            result = ffmpeg_ops.upscale_video(self.selected_file, output_path)
            
            if result:
                self.status_label.SetLabel(f"✅ Success: {os.path.basename(result)}")
                messagebox.showinfo("Success", f"Video upscaled successfully!\n{result}")
            else:
                self.status_label.SetLabel("❌ Upscale failed")
                messagebox.showerror("Error", "Failed to upscale video. Check the log for details.")
        
        except Exception as e:
            self.status_label.SetLabel("❌ Error occurred")
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
        
        finally:
            self.upscale_btn.Enable()


class ClipperPanel(wx.Panel):
    """Placeholder panel for Clipper functionality (coming soon)."""
    
    def __init__(self, parent, app_state):
        """Initialize Clipper panel."""
        super().__init__(parent)
        self.app_state = app_state
        
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Title
        title = wx.StaticText(self, label="Video Clipper")
        title_font = wx.Font(12, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        title.SetFont(title_font)
        main_sizer.Add(title, 0, wx.ALL, 10)
        
        # Coming soon message
        coming_soon = wx.StaticText(self, label="🚧 Coming Soon 🚧")
        coming_soon_font = wx.Font(16, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        coming_soon.SetFont(coming_soon_font)
        coming_soon.SetForegroundColour(wx.Colour(255, 165, 0))
        main_sizer.Add(coming_soon, 0, wx.ALIGN_CENTER | wx.ALL, 20)
        
        info_text = wx.StaticText(self, label="The Video Clipper feature will allow you to extract clips from videos.\nStay tuned for updates!")
        info_text.SetForegroundColour(wx.Colour(128, 128, 128))
        main_sizer.Add(info_text, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        
        self.SetSizer(main_sizer)
