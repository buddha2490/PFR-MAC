# Running PFR Sentinel on macOS

The application is pure Python (PySide6 + qfluentwidgets) and runs natively on
Apple Silicon. Verified on macOS 26.5 / Apple M4 Pro with a **ZWO ASI662MC**.

No Homebrew, no `sudo`, and no admin rights are required.

---

## Quick start

```bash
cd PFRSentinel
./start.sh                 # normal GUI
./start.sh --auto-start    # GUI, begin capturing immediately
./start.sh --headless      # no GUI, web server only
```

---

## First-time setup

The project uses [uv](https://docs.astral.sh/uv/) to manage Python, so the
system Python (3.9 on stock macOS — too old for this app) is left alone.

```bash
# 1. Install uv (no sudo; installs to ~/.local/bin)
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

# 2. Create the virtualenv and install dependencies
cd PFRSentinel
uv venv --python 3.12 .venv
uv pip install -r requirements.txt
```

The ZWO SDK is already vendored in the repo (see below) — nothing else to install.

---

## The ZWO ASI SDK on macOS

`ASICamera2.dll` is Windows-only. The macOS equivalent lives in the repo at:

```
sdk/macos/libASICamera2.dylib    # ZWO ASI SDK v1.41, arm64
sdk/macos/libusb-1.0.0.dylib     # libusb 1.0.27, arm64
```

**Why libusb ships alongside it.** ZWO's stock `libASICamera2.dylib` links
against libusb with a hard-coded Homebrew path:

```
/opt/homebrew/opt/libusb/lib/libusb-1.0.0.dylib
```

That makes the SDK unusable without Homebrew, and it silently breaks whenever
Homebrew bumps the libusb version. The vendored copy is relinked to load the
libusb sitting next to it instead, then ad-hoc re-signed (macOS invalidates a
Mach-O signature after `install_name_tool` rewrites a load command):

```bash
install_name_tool -change /opt/homebrew/opt/libusb/lib/libusb-1.0.0.dylib \
    @loader_path/libusb-1.0.0.dylib sdk/macos/libASICamera2.dylib
install_name_tool -id @loader_path/libusb-1.0.0.dylib sdk/macos/libusb-1.0.0.dylib
codesign --force --sign - sdk/macos/libusb-1.0.0.dylib
codesign --force --sign - sdk/macos/libASICamera2.dylib
```

Verify with `otool -L sdk/macos/libASICamera2.dylib` — it should reference
`@loader_path/libusb-1.0.0.dylib` and nothing under `/opt/homebrew`.

**Path resolution.** `services/utils_paths.py` picks the right library per
platform (`asi_sdk_filename()` / `asi_sdk_candidates()`), searching the
vendored `sdk/<platform>/` directory first, then the app directory, then
system prefixes. No configuration needed; the Capture page's SDK field can
still override it.

**Upgrading the SDK.** Download `ASI_Camera_SDK.zip` from ZWO, extract
`ASI_linux_mac_SDK_*/lib/mac_arm64/libASICamera2.dylib`, drop it into
`sdk/macos/`, and re-run the two `install_name_tool` commands plus `codesign`.

---

## Where files live

Windows uses `%LOCALAPPDATA%\PFRSentinel`. macOS uses the platform convention:

```
~/Library/Application Support/PFRSentinel/
├── config.json
├── logs/
├── Images/
├── Library/          # image library database
└── timelapse/        # default when timelapse output_dir is blank
```

Everything resolves through `services/utils_paths.get_app_data_dir()`.

---

## Viewing the feed from other machines (Tailscale)

The web server is bound to this Mac's **Tailscale address**, so the feed is
reachable from any device on the tailnet and from nowhere else:

| Endpoint  | What it serves                                        |
|-----------|-------------------------------------------------------|
| `/live`   | Auto-refreshing viewer page (also served at `/`)      |
| `/latest` | The latest processed frame (raw image)                |
| `/status` | JSON: capture state, health, image age, metadata      |
| `/docs`   | API documentation                                     |
| `/library`| Browsable image library (when enabled)                |

Configure under **Output → Web Server**, or in `config.json`:

```json
"output": {
  "webserver_enabled": true,
  "webserver_host": "100.126.65.43",
  "webserver_port": 8080
}
```

> **On the bind address.** These endpoints have **no authentication**. Binding
> the Tailscale IP limits reach to your own tailnet. Setting `0.0.0.0` instead
> would also expose the feed on whatever café or hotel Wi-Fi the Mac joins.
> Prefer the Tailscale address unless you specifically want LAN access.
>
> The Tailscale IP is stable per machine, but if it ever changes
> (`tailscale ip -4`), update the config to match — the server cannot bind an
> address the machine does not have, and startup will fail.

---

## Timelapse

`services/ffmpeg_utils.get_ffmpeg_path()` searches, in order: `PATH`, the
Windows winget folder, `/opt/homebrew/bin` and `/usr/local/bin`, the copy
inside a frozen app bundle, then `imageio-ffmpeg`'s binary. That binary is a
normal pip dependency and is bundled into the `.app`, so timelapse works out of
the box with no system ffmpeg.

The Homebrew paths are checked explicitly because an app launched from Finder
inherits a minimal `PATH` that excludes `/opt/homebrew/bin`.

---

## Platform notes

- **USB recovery.** Windows can disable/re-enable the camera's USB device to
  recover a wedged connection. There is no macOS equivalent, so that path is
  skipped; ordinary reconnect logic still runs.
- **Administrator checks** are Windows-only and are skipped rather than logging
  a misleading "run as Administrator" warning.
- **`WARNING:root:ASI SDK library not found`** printed at import is emitted by
  the `zwoasi` package when the `ZWO_ASI_LIB` environment variable is unset.
  It is harmless — the app initialises the SDK explicitly by path afterwards.

---

## Building a shareable installer

```bash
./build_macos.sh
```

Produces `dist/PFRSentinel-<version>-arm64.dmg` (~277 MB) containing
`PFRSentinel.app`, an Applications symlink, and `INSTALL-MACOS.txt`. The app is
self-contained: Python, Qt, the ZWO SDK, and ffmpeg all ride along, so a
recipient installs nothing else.

The script drives `PFRSentinel-macos.spec` (kept separate from the Windows
`PFRSentinel.spec`, which imports `PyInstaller.utils.win32.versioninfo` at
module scope and cannot be parsed on macOS), then re-signs the vendored ZWO
dylibs, signs the bundle, and builds the DMG. It aborts if the bundled
`libASICamera2.dylib` still references `/opt/homebrew`.

### Gatekeeper

The default build is **ad-hoc signed**, which is free but not notarized.
macOS quarantines it on download, so the first launch must be
right-click → Open. `docs/INSTALL-MACOS.txt` ships inside the DMG explaining
this. Recipients can also clear it with:

```bash
xattr -dr com.apple.quarantine /Applications/PFRSentinel.app
```

To remove that friction you need an Apple Developer account ($99/yr) and a
Developer ID Application certificate:

```bash
./build_macos.sh --sign "Developer ID Application: Your Name (TEAMID)"
./build_macos.sh --sign "..." --notarize <keychain-profile>
```

Create the notarization profile once with
`xcrun notarytool store-credentials`. Signing enables the hardened runtime plus
the JIT / unsigned-memory / USB entitlements that the bundled Python, Qt, and
libusb require.

### Two macOS packaging gotchas this build works around

1. **cv2 recursion.** A `.app` ends up with two real `cv2` package directories
   (`Contents/Frameworks/cv2` and `Contents/Resources/cv2`). OpenCV's loader
   compares `realpath(__file__)` against `sys.path[0]`, concludes its sys.path
   workaround is unnecessary, inserts the extension directory at index 1, and
   then re-imports the *package* instead of `cv2.abi3.so` — raising
   *"recursion is detected during loading of cv2 binary extensions"*.
   `hooks/rthook_cv2_macos_app.py` sets OpenCV's own
   `sys.OpenCV_REPLACE_SYS_PATH_0` override to force index 0.

2. **ffmpeg discovery.** `services/ffmpeg_utils.py` finds the bundled binary by
   globbing `sys._MEIPASS/imageio_ffmpeg/binaries/ffmpeg*` rather than calling
   `imageio_ffmpeg.get_ffmpeg_exe()`, so packaging does not depend on that
   package's `__file__`-based lookup surviving freezing.

### Only Apple Silicon

The build is arm64-only — the vendored ZWO SDK is `mac_arm64`, and the
installed wheels are arm64. A universal2 build would need universal Python and
wheels plus a second (x86_64) libusb and ZWO dylib. `build_macos.sh` refuses to
run on a non-arm64 machine.

---

## Tests

```bash
.venv/bin/python -m pytest -q
```

Two known non-macOS failures:

- `tests/test_ml_classifiers.py` — 2 tests need PyTorch, which is not in
  `requirements.txt` (production inference uses ONNX). Fails on Windows too
  without a manual `pip install torch`.
- The full run exits **139** *after* reporting 100%. That is a PySide6/Qt
  destructor segfault during interpreter teardown when many Qt widget tests
  accumulate in one process — a test-harness artifact, not app code. Individual
  test files exit 0.
