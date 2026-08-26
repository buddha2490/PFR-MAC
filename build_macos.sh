#!/bin/bash
# Build PFR Sentinel.app and a distributable .dmg for macOS (Apple Silicon).
#
#   ./build_macos.sh                     # ad-hoc signed (free, no Apple account)
#   ./build_macos.sh --sign "Developer ID Application: Your Name (TEAMID)"
#   ./build_macos.sh --sign "..." --notarize <keychain-profile>
#
# Ad-hoc builds run fine on this machine but are quarantined when downloaded
# elsewhere; recipients must right-click -> Open once. See docs/MACOS.md.

set -euo pipefail
cd "$(dirname "$0")"

SIGN_ID=""
NOTARIZE_PROFILE=""
while [ $# -gt 0 ]; do
    case "$1" in
        --sign)     SIGN_ID="$2"; shift 2 ;;
        --notarize) NOTARIZE_PROFILE="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

VENV=".venv"
PY="$VENV/bin/python"
APP="dist/PFRSentinel.app"
# Match the __version__ line specifically — a bare quote regex picks up the
# module docstring's triple quotes instead.
VERSION=$(sed -n 's/^__version__[[:space:]]*=[[:space:]]*["'"'"']\([^"'"'"']*\)["'"'"'].*/\1/p' version.py)
[ -n "$VERSION" ] || { echo "Could not parse __version__ from version.py"; exit 1; }
DMG="dist/PFRSentinel-${VERSION}-arm64.dmg"

if [ ! -x "$PY" ]; then
    echo "Virtualenv missing at $VENV. See docs/MACOS.md for setup."
    exit 1
fi

if [ "$(uname -m)" != "arm64" ]; then
    echo "This script builds an Apple Silicon (arm64) app; this machine is $(uname -m)."
    exit 1
fi

"$PY" -c "import PyInstaller" 2>/dev/null || {
    echo "==> Installing PyInstaller"
    "${UV:-uv}" pip install pyinstaller
}

echo "==> Building PFR Sentinel $VERSION (arm64)"
rm -rf build dist
"$PY" -m PyInstaller --noconfirm --clean PFRSentinel-macos.spec

[ -d "$APP" ] || { echo "Build failed: $APP not produced."; exit 1; }

# --- Re-sign the vendored ZWO dylibs -------------------------------------
# They ship as `datas` so PyInstaller copies them verbatim and does not rewrite
# the @loader_path load commands. Copying can still drop the signature, and an
# unsigned nested Mach-O makes the whole bundle's signature invalid on arm64
# (where all code must be signed), so sign them before the bundle itself.
echo "==> Signing vendored ZWO SDK"
SDK_IN_APP="$APP/Contents/Frameworks/sdk/macos"
[ -d "$SDK_IN_APP" ] || SDK_IN_APP="$APP/Contents/Resources/sdk/macos"
if [ -d "$SDK_IN_APP" ]; then
    # libusb first: libASICamera2 links against it.
    for lib in "$SDK_IN_APP"/libusb-1.0.0.dylib "$SDK_IN_APP"/libASICamera2.dylib; do
        [ -f "$lib" ] || continue
        codesign --force --sign "${SIGN_ID:--}" --timestamp=none "$lib"
        echo "    signed $(basename "$lib")"
    done
    otool -L "$SDK_IN_APP/libASICamera2.dylib" | grep -q "/opt/homebrew" && {
        echo "ERROR: bundled libASICamera2.dylib still references /opt/homebrew."
        echo "       Re-run the install_name_tool steps in docs/MACOS.md."
        exit 1
    }
else
    echo "ERROR: ZWO SDK missing from the bundle; the camera would not work."
    exit 1
fi

# --- Sign the app bundle --------------------------------------------------
echo "==> Signing app bundle"
if [ -n "$SIGN_ID" ]; then
    # Hardened runtime is required for notarization. The bundled Python and
    # Qt need these two exemptions or the app is killed on launch.
    cat > /tmp/pfrsentinel-entitlements.plist <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>com.apple.security.cs.allow-jit</key><true/>
  <key>com.apple.security.cs.allow-unsigned-executable-memory</key><true/>
  <key>com.apple.security.device.usb</key><true/>
</dict></plist>
PLIST
    codesign --force --deep --options runtime --timestamp \
        --entitlements /tmp/pfrsentinel-entitlements.plist \
        --sign "$SIGN_ID" "$APP"
else
    codesign --force --deep --sign - "$APP"
fi
codesign --verify --deep --strict "$APP" && echo "    signature valid"

# --- Build the DMG --------------------------------------------------------
echo "==> Building DMG"
rm -f "$DMG"
STAGE=$(mktemp -d)
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"
cp docs/INSTALL-MACOS.txt "$STAGE/" 2>/dev/null || true
hdiutil create -volname "PFR Sentinel $VERSION" -srcfolder "$STAGE" \
    -ov -format UDZO "$DMG" >/dev/null
rm -rf "$STAGE"

if [ -n "$SIGN_ID" ]; then
    codesign --force --sign "$SIGN_ID" "$DMG"
fi

# --- Notarize (optional) --------------------------------------------------
if [ -n "$NOTARIZE_PROFILE" ]; then
    [ -n "$SIGN_ID" ] || { echo "--notarize requires --sign"; exit 1; }
    echo "==> Notarizing (this can take several minutes)"
    xcrun notarytool submit "$DMG" --keychain-profile "$NOTARIZE_PROFILE" --wait
    xcrun stapler staple "$DMG"
    echo "    notarized and stapled"
fi

echo
echo "Built: $DMG  ($(du -h "$DMG" | cut -f1))"
if [ -z "$NOTARIZE_PROFILE" ]; then
    echo
    echo "This build is not notarized. Tell recipients to right-click the app"
    echo "and choose Open the first time (see docs/INSTALL-MACOS.txt)."
fi
