# PFR Sentinel — macOS

macOS (Apple Silicon) build of **PFR Sentinel**, a live camera monitoring and
overlay system for observatories.

This repo is a macOS distribution fork — it carries the installer and the
instructions for building one. The application itself is the work of
[**englishfox90**](https://github.com/englishfox90); see
[Credit](#credit-and-license) below.

---

## Download

**[⬇ PFRSentinel-3.6.9-arm64.dmg](https://github.com/buddha2490/PFR-MAC/releases/download/v3.6.9/PFRSentinel-3.6.9-arm64.dmg)** (281 MB)

Or browse [the latest release](https://github.com/buddha2490/PFR-MAC/releases/latest).

| | |
|---|---|
| Version | 3.6.9 |
| Architecture | Apple Silicon (arm64) — **not** Intel |
| Requires | macOS 12 or later, M1 or newer |
| SHA-256 | `15675973d55943ea5c7ae23f9b0880ba7b9277ec0d5616a10024b775d6a4a5c0` |

Verify the download before installing:

```bash
shasum -a 256 ~/Downloads/PFRSentinel-3.6.9-arm64.dmg
```

> **This repo is private.** The link above only resolves while you are signed in
> to a GitHub account with access. From a terminal:
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

Nothing else is required — Python, Qt, the ZWO ASI SDK, and ffmpeg are all
bundled inside the app. Full post-install notes (camera setup, the web feed,
timelapse, data locations) are in [INSTALL-MACOS.txt](INSTALL-MACOS.txt).

---

## Compiling the installer on another Mac

You need an **Apple Silicon Mac** — the build is arm64-only, because the
vendored ZWO SDK is `mac_arm64` and the installed wheels are arm64.
`build_macos.sh` refuses to run on anything else. No Homebrew, no `sudo`, and
no admin rights are needed.

### 1. Get the source

```bash
git clone https://github.com/englishfox90/PFRSentinel.git
cd PFRSentinel
```

### 2. Install uv and build the virtualenv

The project uses [uv](https://docs.astral.sh/uv/) to manage Python so that
stock macOS Python (3.9 — too old for this app) is left alone.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

uv venv --python 3.12 .venv
uv pip install -r requirements.txt
uv pip install pyinstaller
```

The ZWO ASI SDK is already vendored in the repo at `sdk/macos/`, so there is
nothing to download from ZWO.

### 3. Build

```bash
./build_macos.sh
```

That produces `dist/PFRSentinel-<version>-arm64.dmg` containing the app, an
Applications symlink, and the install notes. The version comes from
`__version__` in `version.py`, so bump that before building a new release.

The script drives `PFRSentinel-macos.spec` (kept separate from the Windows
`PFRSentinel.spec`, which cannot even be parsed on macOS), re-signs the
vendored ZWO dylibs, signs the bundle, then builds the DMG. It aborts if the
bundled `libASICamera2.dylib` still references `/opt/homebrew`.

Verify the result before shipping it:

```bash
hdiutil verify dist/PFRSentinel-<version>-arm64.dmg
shasum -a 256 dist/PFRSentinel-<version>-arm64.dmg
```

### 4. Optional — sign and notarize

The default build is ad-hoc signed: free, but quarantined on download, which
is why recipients need right-click → Open. Removing that friction needs an
Apple Developer account ($99/yr) and a Developer ID Application certificate:

```bash
./build_macos.sh --sign "Developer ID Application: Your Name (TEAMID)"
./build_macos.sh --sign "..." --notarize <keychain-profile>
```

Create the notarization profile once with `xcrun notarytool store-credentials`.
Signing enables the hardened runtime plus the JIT, unsigned-memory, and USB
entitlements that the bundled Python, Qt, and libusb require.

### Troubleshooting

| Symptom | Cause |
|---|---|
| `This script builds an Apple Silicon (arm64) app` | Running on Intel. Not supported. |
| `Virtualenv missing at .venv` | Step 2 was skipped or run in the wrong directory. |
| `bundled libASICamera2.dylib still references /opt/homebrew` | The vendored SDK lost its relinking; re-run the `install_name_tool` steps in the source repo's `docs/MACOS.md`. |
| `ERROR: ZWO SDK missing from the bundle` | `sdk/macos/` is absent from the checkout — the camera would not work, so the build stops. |

The source repo's `docs/MACOS.md` is the deeper reference: SDK relinking, the
cv2 recursion and ffmpeg-discovery packaging workarounds, and the test notes.

---

## Publishing a new build to this repo

```bash
./build_macos.sh
gh release create vX.Y.Z dist/PFRSentinel-X.Y.Z-arm64.dmg \
    --repo buddha2490/PFR-MAC \
    --title "PFR Sentinel X.Y.Z" \
    --notes "macOS (Apple Silicon) build."
```

Then update the version, size, download link, and SHA-256 in the table above.

The DMG is never committed to git — at ~281 MB it is far over GitHub's 100 MB
per-file limit, so it lives only as a release asset. `.gitignore` excludes
`*.dmg` and `dist/` to keep that from happening by accident.

---

## Credit and license

PFR Sentinel is created and maintained by
[**englishfox90**](https://github.com/englishfox90) —
[englishfox90/PFRSentinel](https://github.com/englishfox90/PFRSentinel).
All credit for the application belongs to the original author. This repo adds
only macOS packaging and distribution.

Released under the MIT License, Copyright (c) 2025 englishfox90. The full
license text is in [LICENSE](LICENSE).
