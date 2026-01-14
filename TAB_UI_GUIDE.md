# wxPython Notebook Tabbed UI - Implementation Guide

## Overview

This document describes the new tabbed UI implementation for the Glidly Pro AI Automator application using wxPython Notebook.

## Architecture

### Main Window Structure

The application now features a tabbed interface with four main tabs:

1. **Video Generator** - Generate videos using different methods
2. **Video Processor** - Process videos (merge, upscale, clip)
3. **Video Uploader** - Upload videos to various platforms
4. **Livestream** - Stream content live to platforms

### Tab Organization

```
Main Window (MainWindow)
├── Title
├── Notebook (4 top-level tabs)
│   ├── Video Generator (VideoGeneratorTab)
│   │   ├── Default (DefaultGeneratorPanel)
│   │   ├── Nexa (NexaGeneratorPanel)
│   │   ├── Flow Video Generator (FlowGeneratorPanel)
│   │   └── Google Flow (GoogleFlowGeneratorPanel)
│   ├── Video Processor (VideoProcessorTab)
│   │   ├── Merge Video (MergeVideoPanel)
│   │   ├── Upscale to 4K (UpscalePanel)
│   │   └── Clipper (ClipperPanel) [Coming Soon]
│   ├── Video Uploader (VideoUploaderTab)
│   │   ├── YouTube (YouTubeUploaderPanel)
│   │   ├── Facebook (PlaceholderPanel) [Coming Soon]
│   │   ├── TikTok (PlaceholderPanel) [Coming Soon]
│   │   └── Instagram (PlaceholderPanel) [Coming Soon]
│   └── Livestream (LivestreamTab)
│       ├── YouTube (YouTubeLivestreamPanel)
│       ├── Facebook (PlaceholderLivestreamPanel) [Coming Soon]
│       ├── TikTok (PlaceholderLivestreamPanel) [Coming Soon]
│       └── Instagram (PlaceholderLivestreamPanel) [Coming Soon]
├── Activity Log (TextCtrl)
└── Control Buttons (START, PAUSE, STOP)
```

## Features Implemented

### 1. Video Generator Tab

#### Sub-tabs:

- **Default**: Uses Playwright with nexa_extension for captcha solving
  - All standard generation features
  - Extension-based captcha solving
  - Supports Default and Flow generation methods
  
- **Nexa**: Like Default but WITHOUT extensions
  - No captcha solver (for when it causes issues)
  - Cleaner browser profile
  - Implemented via `use_extensions=False` parameter in DefaultRunner
  
- **Flow Video Generator**: Uses FlowEditorRunner
  - Seed image support
  - Account rotation
  - Persistent sessions
  
- **Google Flow**: Google Labs Flow integration
  - **FIXED**: Credentials panel uses wx.Panel instead of StaticBoxSizer.Show()
  - Username and password inputs
  - Session persistence
  - Lazy-imports Google APIs

### 2. Video Processor Tab

#### Sub-tabs:

- **Merge Video**: Combine numbered videos
  - Optional intro prepending
  - Re-encode option for robust merging (fixes concat -c copy issues)
  - FFmpeg-based processing
  
- **Upscale to 4K**: Upscale videos to 4K resolution
  - Lanczos scaling
  - Quality preservation
  - Progress feedback
  
- **Clipper**: [Coming Soon]
  - Placeholder panel with "Coming Soon" message

### 3. Video Uploader Tab

#### Sub-tabs:

- **YouTube**: Full channel mapping per mode
  - Channel name configuration
  - Credentials file selection per mode
  - Save button writes to `youtube_channels.json`
  - Pipeline reads configuration automatically
  
- **Facebook**, **TikTok**, **Instagram**: [Coming Soon]
  - Placeholder panels with "Coming Soon" messages

### 4. Livestream Tab

#### Sub-tabs:

- **YouTube Livestream**: Complete livestream workflow
  - **Authenticate**: Google OAuth authentication
  - **Create Broadcast**: Create YouTube livestream broadcast
  - **Start Video**: Stream video file at 240p
  - **Check Connection**: Verify stream status
  - **Go Live**: Transition broadcast to live
  - **Stop Stream**: Terminate stream
  - **Status Button**: Current livestream status
  - Activity log for debugging
  - Configuration persistence (config.ini)
  - Lazy-import of Google API libraries (no import errors when not used)
  
- **Facebook**, **TikTok**, **Instagram**: [Coming Soon]
  - Placeholder panels for future implementation

## Fixed Issues from PR #1

### 1. wxAssertionError Fix

**Problem**: Calling `.Show()` on a `StaticBoxSizer` caused wxAssertionError when toggling Google Flow credentials.

**Solution**: Used a `wx.Panel` container for Google Flow credentials instead of trying to show/hide a StaticBoxSizer directly.

```python
# Before (BROKEN):
google_flow_sizer.Show(True)  # ERROR: Can't call Show() on a Sizer

# After (FIXED):
self.cred_panel = wx.Panel(self)  # Panel container
# ... add sizer to panel ...
# Panel can be shown/hidden safely
```

### 2. Stop Button Behavior Fix

**Problem**: Pressing STOP didn't immediately re-enable START button and didn't cleanly stop background work.

**Solution**: 
- Used `threading.Event` for stop and pause signals
- Immediately re-enable START in `stop_automation()` via `wx.CallAfter()`
- Pipeline checks `stop_event.is_set()` frequently
- Runners clean up properly

```python
# Threading events
self.stop_event = threading.Event()
self.pause_event = threading.Event()

# Stop immediately re-enables START
def stop_automation(self):
    self.stop_event.set()
    wx.CallAfter(self._reset_ui_state)  # Immediate UI update

# Pipeline checks events
while not self.pause_event.is_set() and not self.stop_event.is_set():
    time.sleep(0.5)
if self.stop_event.is_set():
    break
```

## Technical Implementation Details

### Thread Safety

All UI updates from background threads use `wx.CallAfter()`:

```python
def log(self, msg):
    wx.CallAfter(self._append_log, msg)
```

### App State Sharing

Tabs share state through an `app_state` dictionary:

```python
self.app_state = {
    'prompt_folder': self.prompt_folder,
    'mode': self.mode,
    'generator': self.generator,
    # ... other shared state ...
    'log_callback': self.log,
}
```

### Pipeline Integration

Pipeline updated to use threading events:

```python
pipeline = Pipeline(
    config, 
    gen_config, 
    logger,
    stop_event=self.stop_event,
    pause_event=self.pause_event
)
```

### Runner Selection

Factory pattern selects appropriate runner based on subcategory:

```python
if subcategory == "Nexa":
    return DefaultRunner(..., use_extensions=False)
elif subcategory == "Google Flow":
    return GoogleFlowRunner(...)
elif gen_method == "Flow":
    return FlowRunner(...)
else:
    return DefaultRunner(..., use_extensions=True)
```

## File Structure

```
ui/
├── __init__.py
├── main_window.py          # Main window with tabbed interface
├── dialogs.py              # Helper dialogs (messagebox, filedialog)
├── variables.py            # SimpleVar helper class
└── tabs/
    ├── __init__.py
    ├── video_generator_tab.py   # Video Generator tab + sub-panels
    ├── video_processor_tab.py   # Video Processor tab + sub-panels
    ├── video_uploader_tab.py    # Video Uploader tab + sub-panels
    └── livestream_tab.py        # Livestream tab + sub-panels
```

## Usage

### Running the Application

```bash
python automate_complete.py
```

### Selecting Generation Method

1. Click the **Video Generator** tab
2. Select a sub-tab:
   - **Default** - for standard Nexabot with extensions
   - **Nexa** - for Nexabot without extensions
   - **Flow Video Generator** - for Flow method
   - **Google Flow** - for Google Labs Flow

### Merging Videos

1. Click the **Video Processor** tab
2. Click the **Merge Video** sub-tab
3. Select folder with numbered videos
4. Choose options (intro, re-encode)
5. Click **Merge Videos**

### Configuring YouTube Channels

1. Click the **Video Uploader** tab
2. Click the **YouTube** sub-tab
3. For each mode, enter:
   - Channel name
   - Browse for credentials file
4. Click **💾 Save Channel Settings**

### YouTube Livestreaming

1. Click the **Livestream** tab
2. Click the **YouTube** sub-tab
3. Configure paths (client secret, video file)
4. Follow workflow:
   - Authenticate → Create Broadcast → Start Video → Check Connection → Go Live
5. Monitor stream in log area
6. Click **Stop Stream** when done

## Configuration Files

### youtube_channels.json

```json
{
  "Shorts": {
    "name": "My Shorts Channel",
    "credentials": "/path/to/shorts_token.json"
  },
  "Sound Relief": {
    "name": "Relaxation Channel",
    "credentials": "/path/to/relief_token.json"
  },
  "Restorasi": {
    "name": "Restoration Channel",
    "credentials": "/path/to/restorasi_token.json"
  },
  "Home Renovation": {
    "name": "Renovation Channel",
    "credentials": "/path/to/renovation_token.json"
  }
}
```

### livestream_config.ini

```ini
[paths]
client_secret_path = /path/to/client_secret.json
token_path = token_livestream.json
last_video_path = /path/to/video.mp4
```

## Future Enhancements

- [ ] Implement Video Clipper functionality
- [ ] Add Facebook upload support
- [ ] Add TikTok upload support
- [ ] Add Instagram upload support
- [ ] Add Facebook livestream support
- [ ] Add TikTok livestream support
- [ ] Add Instagram livestream support
- [ ] Add batch processing for Video Processor
- [ ] Add preview functionality
- [ ] Add progress bars for long operations

## Troubleshooting

### Import Errors

If you get `ModuleNotFoundError`, install dependencies:

```bash
pip install -r requirements.txt
```

### wxPython Installation Issues

wxPython requires compilation on some platforms. Use pre-built wheels:

```bash
pip install -U -f https://extras.wxpython.org/wxPython4/extras/linux/gtk3/ubuntu-20.04 wxPython
```

### Google API Import Errors

Google API libraries are lazy-imported only when needed. If you don't use YouTube livestream, you don't need these libraries installed.

### Livestream Issues

1. Ensure `client_secret.json` is valid
2. Check internet connection
3. Verify FFmpeg is installed and in PATH
4. Check video file format (MP4 recommended)

## Credits

- Original implementation: PR #1 (Modular Refactor)
- Tabbed UI implementation: This PR
- Google Flow integration: Based on ytstream.py conversion
