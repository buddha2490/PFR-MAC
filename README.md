# PFR Sentinel — macOS

**Live Camera Monitoring & Overlay System for Observatories**

Private macOS (Apple Silicon) fork of
[**englishfox90/PFRSentinel**](https://github.com/englishfox90/PFRSentinel).
All credit for the application belongs to its author, **Paul Fox-Reeks**
([englishfox90](https://github.com/englishfox90)) — this fork adds only the
macOS port and packaging. MIT licensed, Copyright (c) 2025 englishfox90.

---

# ⬇ Download

## **[PFRSentinel-3.6.9-arm64.dmg](https://github.com/buddha2490/PFR-MAC/releases/download/v3.6.9/PFRSentinel-3.6.9-arm64.dmg)**

**281 MB** · Apple Silicon (arm64) · macOS 12 or later

[![Latest release](https://img.shields.io/badge/release-v3.6.9-blue)](https://github.com/buddha2490/PFR-MAC/releases/latest)

| | |
|---|---|
| Version | 3.6.9 |
| Architecture | Apple Silicon (arm64) — **not** Intel |
| Requires | macOS 12 or later, M1 or newer |
| SHA-256 | `15675973d55943ea5c7ae23f9b0880ba7b9277ec0d5616a10024b775d6a4a5c0` |

Verify before installing:

```bash
shasum -a 256 ~/Downloads/PFRSentinel-3.6.9-arm64.dmg
```

> **This repo is private.** The link works while you are signed in to a GitHub
> account with access. From a terminal instead:
>
> ```bash
> gh release download v3.6.9 --repo buddha2490/PFR-MAC
> ```

### Install

1. Open the DMG and drag **PFRSentinel.app** onto the Applications folder.
2. **First launch only:** right-click (or Control-click) PFRSentinel in
   Applications and choose **Open**, then **Open** in the dialog.

   A plain double-click will not work the first time. This build is ad-hoc
   signed rather than notarized by Apple, so macOS shows *"Apple could not
   verify PFRSentinel is free of malware."* Every later launch is normal.

   If it still refuses:

   ```bash
   xattr -dr com.apple.quarantine /Applications/PFRSentinel.app
   ```

Nothing else to install — Python, Qt, the ZWO ASI SDK, and ffmpeg all ride
along inside the app.

**→ [Full install notes and how to compile the installer on another Mac](docs/DOWNLOAD.md)**

---

# About the application

A modern astrophotography application with a Fluent Design UI (PySide6 + qfluentwidgets) that watches directories for new images or captures directly from ZWO ASI cameras, adding customizable metadata overlays with weather data and serving output through multiple channels.

**Current Version:** 3.6.9

---

## Key Features

### Capture Modes
- **Directory Watch Mode**: Monitor folders for new images from any camera/software
- **ZWO Camera Mode**: Direct capture from ZWO ASI cameras with auto-exposure and debayering

### Output Modes (can run simultaneously)
- **File Output**: Save processed images to disk
- **Web Server**: HTTP server with `/live` (auto-refreshing viewer page), `/latest` (image) and `/status` (JSON) endpoints
- **Discord Integration**: Periodic image posts with weather data embeds

### Processing
- Auto-stretch (MAD-based histogram stretching)
- Customizable text overlays with metadata tokens
- Weather data integration (OpenWeatherMap)
- Resize and format options (PNG/JPEG)

### User Interface
- Modern Fluent Design UI (Windows 11 styling)
- Live monitoring panel with preview, RGB histogram, and mini-log
- System tray support with notifications
- Command-line automation support (`--headless`, `--auto-start`, `--tray`)

---

## Running from source

The recommended install for macOS is the **[DMG at the top of this page](#-download)** —
it is self-contained and needs nothing else. To run from source instead:

### macOS (Apple Silicon)

The ZWO SDK is vendored in `sdk/macos/`, so no Homebrew and no `sudo` are
needed. See **[docs/MACOS.md](docs/MACOS.md)** for full setup.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # first time only
git clone https://github.com/buddha2490/PFR-MAC.git
cd PFR-MAC
uv venv --python 3.12 .venv && uv pip install -r requirements.txt
./start.sh
```

### Windows

Upstream ships a Windows installer; see
[englishfox90/PFRSentinel](https://github.com/englishfox90/PFRSentinel).
To run from source:

```powershell
git clone https://github.com/englishfox90/PFRSentinel.git
cd PFRSentinel
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Optional on either platform: an **OpenWeatherMap API key** for weather
overlays. ffmpeg is bundled, so timelapse needs no extra install.

---

## Quick Start

1. **Choose Capture Mode** (Capture page):
   - **Directory Watch**: Select folder to monitor for new images
   - **ZWO Camera**: Click "Detect Cameras", configure exposure/gain

2. **Configure Outputs** (Output page):
   - Enable desired outputs (File, Web, Discord)
   - Configure settings for each

3. **Add Overlays** (Overlays page):
   - Add text overlays with tokens like `{CAMERA}`, `{EXPOSURE}`, `{WEATHER}`

4. **Monitor** (Monitoring page):
   - View live preview, histogram, and recent logs

---

## Command Line Options

```powershell
python main.py --auto-start              # Auto-start capture
python main.py --auto-stop 3600          # Stop after N seconds
python main.py --headless                # No GUI (server mode)
python main.py --tray                    # Start minimized to tray
```

---

## Project Structure

```
PFRSentinel/
├── ui/                        # PySide6 + qfluentwidgets UI
│   ├── main_window.py         # Main application window
│   ├── system_tray_qt.py      # System tray integration
│   ├── components/            # Reusable UI components (app_bar, cards, nav_rail)
│   ├── panels/                # Main pages
│   │   ├── capture_settings.py
│   │   ├── output_settings.py
│   │   ├── overlay_settings.py
│   │   ├── live_monitoring.py
│   │   └── logs_panel.py
│   ├── controllers/           # Business logic
│   │   ├── camera_controller.py
│   │   ├── watch_controller.py
│   │   └── image_processor.py
│   └── theme/                 # Fluent Design theming
├── services/                  # Core processing modules
│   ├── config.py              # JSON persistence (%APPDATA%\PFRSentinel)
│   ├── logger.py              # Thread-safe logging
│   ├── processor.py           # Image overlay engine
│   ├── watcher.py             # Directory monitoring
│   ├── zwo_camera.py          # ZWO ASI SDK wrapper
│   ├── discord_alerts.py      # Discord webhook client
│   ├── weather.py             # OpenWeatherMap integration
│   └── web_output.py          # HTTP server
├── main.py                    # Application entry point
├── app_config.py              # App identity configuration
└── version.py                 # Version info
```

---

## Configuration

Settings stored in `%APPDATA%\PFRSentinel\config.json`

Logs in `%APPDATA%\PFRSentinel\logs` (7-day rotation)

---

## Overlay Tokens

| Token | Description |
|-------|-------------|
| `{CAMERA}` | Camera name |
| `{EXPOSURE}` | Exposure time |
| `{GAIN}` | Gain value |
| `{TEMP}` | Camera/weather temperature |
| `{FILENAME}` | Original filename |
| `{DATETIME}` | Current date/time |
| `{WEATHER}` | Weather description |
| `{WEATHER_ICON}` | Weather icon emoji |

---

## Troubleshooting

- **No cameras detected**: Verify USB connection, check SDK path in Capture page
- **Weather shows N/A**: Configure API key and location in settings
- **Check logs**: Use Logs page or open `%APPDATA%\PFRSentinel\logs`

---

## Building

### macOS (Apple Silicon)

```bash
./build_macos.sh    # -> dist/PFRSentinel-<version>-arm64.dmg
```

Full details, signing, and notarization: **[docs/DOWNLOAD.md](docs/DOWNLOAD.md)**
and **[docs/MACOS.md](docs/MACOS.md)**.

### Windows

```powershell
.\build_sentinel.bat           # Build executable
.\build_sentinel_installer.bat # Build installer
```

---

## License and credit

PFR Sentinel is created and maintained by **Paul Fox-Reeks**
([englishfox90](https://github.com/englishfox90)) —
[englishfox90/PFRSentinel](https://github.com/englishfox90/PFRSentinel).
All credit for the application belongs to him; this fork adds only the macOS
port and packaging.

MIT License, Copyright (c) 2025 englishfox90 — see [LICENSE](LICENSE).

