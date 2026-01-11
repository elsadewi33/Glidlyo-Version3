# Glidlyo - Version 3

AI-powered video automation tool with modular architecture and tabbed UI.

## Features

- **Tabbed Interface**: Organized workspace with 4 main tabs
  - Video Generator (Default, Nexa, Flow, Google Flow)
  - Video Processor (Merge, Upscale, Clipper)
  - Video Uploader (YouTube + more coming soon)
  - Livestream (YouTube + more coming soon)

- **Multiple Generation Methods**:
  - Default: Playwright with Nexabot extensions (captcha solving)
  - Nexa: Playwright without extensions (cleaner, no captcha solver)
  - Flow: FlowEditorRunner with seed image support
  - Google Flow: Google Labs Flow integration

- **Video Processing**:
  - Merge videos with optional intro
  - Upscale to 4K resolution
  - Robust re-encoding for compatibility

- **YouTube Integration**:
  - Channel mapping per mode
  - Automated uploads with thumbnails
  - Live streaming with full workflow

## Usage

Run the application:
```bash
python automate_complete.py
```

## Quick Start

1. **Configure Environment**: Create `.env` file with:
   ```
   GLID_EMAIL=your_email
   GLID_PWD=your_password
   DOWNLOAD_PATH=/path/to/downloads
   FFMPEG_EXE=/path/to/ffmpeg
   ASSETS_FOLDER=./Assets
   ```

2. **Select Generation Mode**:
   - Open **Video Generator** tab
   - Choose sub-tab (Default/Nexa/Flow/Google Flow)
   - Select JSON prompt folder
   - Configure settings
   - Click START

3. **Process Videos**:
   - Open **Video Processor** tab
   - Choose Merge or Upscale
   - Follow on-screen instructions

4. **Upload to YouTube**:
   - Open **Video Uploader** tab → YouTube
   - Configure channel mappings
   - Save settings

5. **Livestream**:
   - Open **Livestream** tab → YouTube
   - Authenticate and configure
   - Follow workflow buttons

## Documentation

- [Tabbed UI Guide](TAB_UI_GUIDE.md) - Detailed UI documentation
- [Refactoring Summary](REFACTORING_SUMMARY.md) - Architecture details

## Architecture

The application follows a modular architecture:

- `core/` - Configuration, models, utilities, and logging
- `ui/` - wxPython user interface with tabbed layout
  - `ui/tabs/` - Tab panels (Video Generator, Processor, Uploader, Livestream)
- `services/` - Orchestration pipeline
- `generation/` - Video generation methods (Default, Nexa, Flow, Google Flow)
- `media/` - FFmpeg operations (merge, upscale, sound relief)

## Requirements

- Python 3.8+
- wxPython
- playwright
- python-dotenv
- google-api-python-client (for YouTube features)
- google-auth-oauthlib (for YouTube features)

Install dependencies:
```bash
pip install -r requirements.txt
```

## New in This Version

### Fixed Issues
- ✅ Fixed wxAssertionError when toggling Google Flow credentials (now uses Panel instead of Sizer.Show())
- ✅ Fixed Stop button behavior (immediate UI update, threading.Event for clean shutdown)
- ✅ Robust video merging with re-encoding option (fixes concat -c copy issues)

### New Features
- ✅ Tabbed UI with wx.Notebook (4 main tabs, nested sub-tabs)
- ✅ Nexa generator mode (Default without extensions)
- ✅ YouTube channel mapping UI (per-mode configuration)
- ✅ YouTube livestream panel (full workflow integration)
- ✅ Video processor standalone tools
- ✅ Placeholder tabs for future platforms (Facebook, TikTok, Instagram)

Configure environment variables in `.env` file.
