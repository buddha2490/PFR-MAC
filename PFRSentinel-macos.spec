# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for PFR Sentinel — macOS (Apple Silicon)

Kept separate from PFRSentinel.spec because that file imports
PyInstaller.utils.win32.versioninfo at module scope, which does not exist on
macOS. Package selection mirrors the Windows spec; the macOS-specific parts are:

  - the vendored ZWO SDK (sdk/macos/*.dylib) instead of ASICamera2.dll
  - a bundled ffmpeg binary, so timelapse works with no system ffmpeg
  - a BUNDLE() step producing PFRSentinel.app with an .icns icon
  - target_arch='arm64'

Build with build_macos.sh (do not call pyinstaller directly — the script also
re-signs the vendored dylibs and builds the .dmg).
"""

import os
import sys
import glob
from PyInstaller.utils.hooks import collect_data_files, collect_all, collect_dynamic_libs

SPEC_DIR = os.path.dirname(os.path.abspath(SPEC))

# ============================================================================
# VERSION (single source of truth: version.py)
# ============================================================================

version_str = "0.0.0"
try:
    with open(os.path.join(SPEC_DIR, 'version.py')) as f:
        for line in f:
            if line.startswith('__version__'):
                version_str = line.split('=')[1].strip().strip('"\'')
                break
    print(f"[OK] Version from version.py: {version_str}")
except Exception as e:
    print(f"[WARN] Could not read version.py: {e}")


def _collect(pkg):
    """collect_all() that degrades to empty rather than failing the build."""
    try:
        d, b, h = collect_all(pkg)
        print(f"[OK] {pkg}: {len(d)} datas, {len(h)} imports")
        return d, b, h
    except Exception as e:
        print(f"[WARN] {pkg}: {e}")
        return [], [], []


datas, binaries, hidden = [], [], []
for _pkg in ('qfluentwidgets', 'requests', 'jaraco', 'pystray', 'platformdirs',
             'posthog', 'backoff', 'scipy',
             'opentelemetry', 'opentelemetry.sdk', 'opentelemetry.exporter.otlp',
             'googleapiclient', 'google_auth_oauthlib', 'google.auth',
             'google.oauth2', 'httplib2', 'oauthlib', 'requests_oauthlib',
             'uritemplate'):
    _d, _b, _h = _collect(_pkg)
    datas += _d
    binaries += _b
    hidden += _h

# --- onnxruntime: core only, not the tooling/transformers tree ---
try:
    datas += collect_data_files('onnxruntime')
    binaries += collect_dynamic_libs('onnxruntime')
    hidden += ['onnxruntime', 'onnxruntime.capi', 'onnxruntime.capi._pybind_state']
    print("[OK] onnxruntime")
except Exception as e:
    print(f"[WARN] onnxruntime: {e}")

# ============================================================================
# DATA FILES
# ============================================================================

added_files = [
    ('version.py', '.'),
    ('assets/app_icon.png', 'assets'),
    ('assets/app_icon.icns', 'assets'),
    # ML models (ONNX for production inference)
    ('ml/models/roof_classifier_v1.onnx', 'ml/models'),
    ('ml/models/sky_classifier_v1.onnx', 'ml/models'),
    # All-sky overlay catalog data
    ('star_data/bsc5-short.json', 'star_data'),
    ('star_data/messier_list.json', 'star_data'),
    ('star_data/NGC.csv', 'star_data'),
    ('star_data/constellations.json', 'star_data'),
]

# --- Vendored ZWO ASI SDK ------------------------------------------------
# Listed under datas so they land at sdk/macos/ where
# services/utils_paths.asi_sdk_candidates() looks first (resource_path()
# resolves that against sys._MEIPASS inside the bundle).
#
# PyInstaller still detects them as Mach-O and rewrites the @loader_path load
# command to @rpath, adding LC_RPATH @loader_path/../.. and a copy of libusb
# at Contents/Frameworks/ — which resolves correctly, so the no-Homebrew
# property is preserved. build_macos.sh re-signs them and asserts that no
# /opt/homebrew reference survived.
_sdk_dir = os.path.join(SPEC_DIR, 'sdk', 'macos')
_sdk_libs = sorted(glob.glob(os.path.join(_sdk_dir, '*.dylib')))
if not _sdk_libs:
    raise SystemExit(
        "ZWO SDK not found in sdk/macos/. The camera would be unusable in the "
        "bundle. See docs/MACOS.md for how to vendor and relink it."
    )
for _lib in _sdk_libs:
    added_files.append((_lib, 'sdk/macos'))
    print(f"[OK] bundling ASI SDK: {os.path.basename(_lib)}")

# --- ffmpeg (timelapse) ---------------------------------------------------
# Recipients will not have Homebrew's ffmpeg. Bundling imageio-ffmpeg's static
# binary makes timelapse work on a clean Mac. services/ffmpeg_utils.py still
# prefers a real ffmpeg on PATH when one exists.
try:
    import imageio_ffmpeg
    _ff = imageio_ffmpeg.get_ffmpeg_exe()
    if _ff and os.path.isfile(_ff):
        added_files.append((_ff, os.path.join('imageio_ffmpeg', 'binaries')))
        print(f"[OK] bundling ffmpeg: {os.path.basename(_ff)}")
except Exception as e:
    print(f"[WARN] ffmpeg not bundled — timelapse will need a system ffmpeg: {e}")

# ============================================================================
# HIDDEN IMPORTS
# ============================================================================

hiddenimports = [
    # --- Core image processing ---
    'PIL', 'PIL.Image', 'PIL.ImageDraw', 'PIL.ImageFont', 'PIL.ImageEnhance',
    'numpy', 'cv2',

    # --- PySide6 ---
    'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets',
    'PySide6.QtSvg', 'PySide6.QtXml',
    'qfluentwidgets',

    # --- HTTP/Network ---
    'requests', 'urllib3', 'certifi', 'charset_normalizer', 'idna',
    'http.server', 'socketserver',

    # --- Analytics (PostHog) ---
    'posthog', 'posthog.client', 'posthog.consumer', 'posthog.request',
    'posthog.version', 'posthog.exception_capture', 'posthog.exception_utils',
    'posthog.feature_flags', 'posthog.poller', 'posthog.utils', 'posthog.types',
    'posthog.contexts', 'posthog.args', 'posthog.flag_definition_cache',
    'backoff', 'six', 'dateutil', 'distro',

    # --- YouTube uploads / Google API client ---
    'googleapiclient', 'googleapiclient.discovery', 'googleapiclient.http',
    'googleapiclient.discovery_cache', 'googleapiclient.discovery_cache.documents',
    'google_auth_oauthlib', 'google_auth_oauthlib.flow',
    'google.auth', 'google.auth.transport.requests', 'google.auth.exceptions',
    'google.oauth2', 'google.oauth2.credentials',
    'httplib2', 'oauthlib', 'requests_oauthlib', 'uritemplate',

    # --- XML ---
    'xml', 'xml.parsers', 'xml.parsers.expat',
    'xml.etree', 'xml.etree.ElementTree',

    # --- File monitoring ---
    'watchdog', 'watchdog.observers', 'watchdog.events',

    # --- System tray (Cocoa backend on macOS, not _win32) ---
    'pystray', 'pystray._base', 'pystray._util', 'pystray._darwin',

    # --- ZWO camera ---
    'zwoasi',

    # --- ffmpeg locator ---
    'imageio_ffmpeg',

    # --- Package management ---
    'importlib.metadata', 'importlib.resources', 'pkg_resources',
    'jaraco', 'jaraco.text', 'jaraco.context', 'jaraco.functools',
    'more_itertools', 'autocommand', 'platformdirs',

    # --- All-sky overlay modules ---
    'services.allsky', 'services.allsky.coords', 'services.allsky.catalogs',
    'services.allsky.planets', 'services.allsky.fisheye',
    'services.allsky.calibration', 'services.allsky.star_centroid',
    'services.allsky.label_collision', 'services.allsky.overlay_renderer',
    'services.allsky.render_grid', 'services.allsky.render_constellations',
    'services.allsky.render_objects', 'services.allsky.config_schema',

    # --- App modules ---
    'services', 'services.config', 'services.logger', 'services.processor',
    'services.watcher', 'services.cleanup', 'services.color_balance',
    'services.web_output', 'services.web_library', 'services.web_live_view',
    'services.api_docs', 'services.discord_alerts', 'services.headless_runner',
    'services.weather', 'services.ml_service', 'services.ascom_safety',
    'services.posthog_service', 'services.posthog_logs',
    'services.ffmpeg_utils', 'services.utils_paths',
    'services.timelapse_writer', 'services.timelapse_finalizer',
    'services.timelapse_frame_pump', 'services.timelapse_publishers',
    'services.youtube_auth', 'services.youtube_config', 'services.youtube_upload',
    'services.youtube_upload_state',
    'services.camera', 'services.camera.zwo_camera',
    'services.camera.camera_connection', 'services.camera.camera_calibration',
    'services.camera.camera_utils', 'services.camera.zwo_capture_worker',
    'ui', 'ui.main_window', 'ui.theme', 'ui.components', 'ui.panels',
    'ui.controllers', 'ui.system_tray_qt',

    # --- ML ---
    'ml', 'ml.roof_classifier', 'ml.sky_classifier', 'onnxruntime',
] + hidden

# ============================================================================
# ANALYSIS
# ============================================================================

a = Analysis(
    ['main.py'],
    pathex=[SPEC_DIR],
    binaries=binaries,
    datas=added_files + datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['hooks/rthook_cv2_macos_app.py'],
    excludes=[
        # Heavy ML stacks — production inference uses ONNX
        'torch', 'torchvision', 'torchaudio',
        'onnx',  # model format package, NOT onnxruntime
        'tensorflow', 'keras',
        'sklearn', 'scikit-learn',
        'pandas', 'matplotlib', 'mpl_toolkits', 'seaborn', 'plotly',
        'astropy',  # FITS, dev-mode only — all-sky is pure numpy
        'sympy',

        # Unused stdlib / old UI
        'tkinter', 'tk', 'tcl', '_tkinter',
        'ttkbootstrap',
        'IPython', 'jupyter', 'notebook',
        'pytest', 'doctest',
        'setuptools', 'wheel', 'pip',
        'lib2to3',
        # NOTE: do NOT exclude 'distutils' — see the Windows spec for why.
        # NOTE: 'unittest' is NOT excluded — scipy imports it at runtime.

        # Unused PySide6 modules. QtNetwork stays: services/single_instance.py
        # uses QLocalServer/QLocalSocket for the single-instance guard.
        'PySide6.QtWebEngine', 'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets',
        'PySide6.Qt3DCore', 'PySide6.Qt3DRender', 'PySide6.Qt3DInput',
        'PySide6.Qt3DLogic', 'PySide6.Qt3DAnimation', 'PySide6.Qt3DExtras',
        'PySide6.QtCharts', 'PySide6.QtDataVisualization',
        'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets',
        'PySide6.QtQuick', 'PySide6.QtQuickWidgets', 'PySide6.QtQuickControls2',
        'PySide6.QtQml', 'PySide6.QtSql', 'PySide6.QtTest',
        'PySide6.QtBluetooth', 'PySide6.QtNfc', 'PySide6.QtSerialPort',
        'PySide6.QtSerialBus', 'PySide6.QtSensors', 'PySide6.QtTextToSpeech',
        'PySide6.QtHelp', 'PySide6.QtDesigner', 'PySide6.QtUiTools',
        'PySide6.QtPrintSupport', 'PySide6.QtConcurrent',
        'PySide6.QtOpenGL', 'PySide6.QtOpenGLWidgets',
        'PySide6.QtRemoteObjects', 'PySide6.QtScxml', 'PySide6.QtStateMachine',
        'PySide6.QtWebSockets', 'PySide6.QtHttpServer', 'PySide6.QtPositioning',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PFRSentinel',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='arm64',
    codesign_identity=None,   # ad-hoc; build_macos.sh signs the finished bundle
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='PFRSentinel',
)

app = BUNDLE(
    coll,
    name='PFRSentinel.app',
    icon='assets/app_icon.icns',
    bundle_identifier='com.paulfoxreeks.pfrsentinel',
    version=version_str,
    info_plist={
        'CFBundleName': 'PFR Sentinel',
        'CFBundleDisplayName': 'PFR Sentinel',
        'CFBundleShortVersionString': version_str,
        'CFBundleVersion': version_str,
        'NSHumanReadableCopyright': 'Copyright (c) 2024-2026 Paul Fox-Reeks',
        'LSMinimumSystemVersion': '12.0',
        # Not a document-based app; keep it out of the "Open With" menus.
        'LSApplicationCategoryType': 'public.app-category.photography',
        # Qt handles HiDPI itself; declaring this avoids a blurry fallback.
        'NSHighResolutionCapable': True,
        # Shown in the macOS permission prompt when libusb first claims the
        # camera. Without a usage string the prompt is blank and confusing.
        'NSCameraUsageDescription':
            'PFR Sentinel captures images from your connected ZWO ASI camera.',
    },
)
