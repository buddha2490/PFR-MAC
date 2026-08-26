"""
Path utilities for PyInstaller resource handling
Resolves paths correctly whether running from source or as bundled EXE
"""
import os
import sys
import tempfile

# Import app configuration for centralized naming
try:
    from .app_config import APP_DATA_FOLDER
except ImportError:
    APP_DATA_FOLDER = "PFRSentinel"  # Fallback


def resource_path(relative_path):
    """
    Get absolute path to resource, works for dev and for PyInstaller

    Args:
        relative_path: Path relative to application root

    Returns:
        Absolute path to resource
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        # Running from source - go up to project root (this file is in services/)
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return os.path.join(base_path, relative_path)


def get_app_data_dir():
    r"""
    Get application data directory (for logs, user config, etc.)

    Returns:
        Path to %LOCALAPPDATA%\{APP_DATA_FOLDER} (Windows)
    """
    if sys.platform == 'win32':
        # Use LOCALAPPDATA on Windows
        local_app_data = os.environ.get('LOCALAPPDATA')
        if not local_app_data:
            # Fallback to APPDATA if LOCALAPPDATA not available
            local_app_data = os.environ.get('APPDATA', os.path.expanduser('~'))
        app_dir = os.path.join(local_app_data, APP_DATA_FOLDER)
    elif sys.platform == 'darwin':
        # macOS convention: ~/Library/Application Support/{APP_DATA_FOLDER}
        app_dir = os.path.join(
            os.path.expanduser('~'), 'Library', 'Application Support', APP_DATA_FOLDER
        )
    else:
        # Fallback for other platforms
        app_dir = os.path.join(os.path.expanduser('~'), f'.{APP_DATA_FOLDER}')

    # Create directory if it doesn't exist. In sandboxed/dev environments the
    # home fallback may be read-only; use the temp directory rather than failing
    # module import. Windows production still uses %LOCALAPPDATA%.
    try:
        os.makedirs(app_dir, exist_ok=True)
    except PermissionError:
        app_dir = os.path.join(tempfile.gettempdir(), APP_DATA_FOLDER)
        os.makedirs(app_dir, exist_ok=True)

    return app_dir


def get_log_dir():
    r"""
    Get log directory path

    Returns:
        Path to %LOCALAPPDATA%\{APP_DATA_FOLDER}\Logs
    """
    log_dir = os.path.join(get_app_data_dir(), 'Logs')
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


def get_ml_contribution_dir():
    r"""
    Get ML data contribution directory path.

    Returns:
        Path to %LOCALAPPDATA%\{APP_DATA_FOLDER}\ml_contribution
    """
    ml_dir = os.path.join(get_app_data_dir(), 'ml_contribution')
    os.makedirs(ml_dir, exist_ok=True)
    return ml_dir


def get_exe_dir():
    """
    Get the directory where the EXE is installed/running from.

    Returns:
        Absolute path to the directory containing the executable (or script in dev mode)
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return os.path.dirname(sys.executable)
    else:
        # Running from source
        return os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------------------
# ZWO ASI SDK library resolution (cross-platform)
# ---------------------------------------------------------------------------

def asi_sdk_filename():
    """Native filename of the ZWO ASI SDK shared library for this platform."""
    if sys.platform == 'win32':
        return 'ASICamera2.dll'
    if sys.platform == 'darwin':
        return 'libASICamera2.dylib'
    return 'libASICamera2.so'


def asi_sdk_candidates():
    """Candidate paths for the ZWO ASI SDK library, best first.

    Windows keeps the DLL next to the app (PyInstaller drops it in _internal),
    so resource_path() alone is enough there. macOS/Linux builds are vendored
    under sdk/<platform>/ because the ZWO SDK ships per-arch libraries and, on
    macOS, links against a sibling libusb we relink at vendor time.
    """
    name = asi_sdk_filename()
    candidates = []

    if sys.platform == 'darwin':
        import platform as _platform
        # Apple Silicon first on arm64, but keep the Intel lib as a fallback so
        # a Rosetta interpreter still finds a library it can actually load.
        arches = ['macos', 'macos-x86_64'] if _platform.machine() == 'arm64' \
            else ['macos-x86_64', 'macos']
        candidates += [resource_path(os.path.join('sdk', a, name)) for a in arches]
    elif sys.platform.startswith('linux'):
        candidates.append(resource_path(os.path.join('sdk', 'linux', name)))

    # App directory (Windows layout, and any manual drop-in)
    candidates.append(resource_path(name))
    candidates.append(os.path.join(get_exe_dir(), name))
    # Bare name last, preserving the previous CWD-relative lookup on Windows.
    candidates.append(name)

    if sys.platform == 'darwin':
        # Homebrew / manual system installs
        candidates += [
            '/opt/homebrew/lib/' + name,
            '/usr/local/lib/' + name,
        ]
    elif sys.platform.startswith('linux'):
        candidates += ['/usr/local/lib/' + name, '/usr/lib/' + name]

    # De-dupe, preserving order
    seen, out = set(), []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def default_asi_sdk_path():
    """Best-guess path to the ZWO ASI SDK library for this platform.

    Returns the first candidate that exists; falls back to the preferred
    candidate so config carries a sensible (if missing) path the user can fix
    in the UI rather than an empty string.
    """
    candidates = asi_sdk_candidates()
    for c in candidates:
        if os.path.isfile(c):
            return c
    return candidates[0]
