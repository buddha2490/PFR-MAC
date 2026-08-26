"""
Shared ffmpeg and winget availability checks.
Used by the timelapse feature.
"""
import glob
import os
import shutil
import subprocess
import sys

# Hide console windows for subprocess calls on Windows
_POPEN_KWARGS = {'creationflags': subprocess.CREATE_NO_WINDOW} if sys.platform == 'win32' else {}


def get_ffmpeg_path() -> str:
    """
    Return the full path to the ffmpeg executable.

    Search order:
    1. System/user PATH (shutil.which)
    2. winget packages folder — Gyan.FFmpeg installs as a zip extract
       to %LOCALAPPDATA%\\Microsoft\\WinGet\\Packages\\ and may not
       add itself to PATH on all winget versions.

    Falls back to the bare string 'ffmpeg' so callers can still attempt
    to run it and get a natural FileNotFoundError if truly absent.
    """
    # 1. PATH check
    path = shutil.which('ffmpeg')
    if path:
        return path

    # 2. winget packages folder (Windows)
    if sys.platform == 'win32':
        winget_base = os.path.join(
            os.getenv('LOCALAPPDATA', ''),
            'Microsoft', 'WinGet', 'Packages'
        )
        for candidate in glob.glob(
            os.path.join(winget_base, 'Gyan.FFmpeg*', '**', 'ffmpeg.exe'),
            recursive=True,
        ):
            if os.path.isfile(candidate):
                return candidate

    # 3. Common package-manager prefixes not always on a GUI app's PATH.
    #    A .app launched from Finder inherits a minimal PATH that excludes
    #    /opt/homebrew/bin, so shutil.which() misses a working Homebrew ffmpeg.
    if sys.platform == 'darwin':
        for candidate in ('/opt/homebrew/bin/ffmpeg', '/usr/local/bin/ffmpeg'):
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate

    # 4. The copy bundled inside a frozen app. Checked by path rather than by
    #    asking imageio_ffmpeg, because its lookup keys off __file__ and we do
    #    not want the packaged app depending on that resolving under PyInstaller.
    meipass = getattr(sys, '_MEIPASS', None)
    if meipass:
        bundled = glob.glob(os.path.join(meipass, 'imageio_ffmpeg', 'binaries', 'ffmpeg*'))
        for candidate in sorted(bundled):
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate

    # 5. imageio-ffmpeg's bundled binary. Installed as a normal Python
    #    dependency, so this makes timelapse work with no system ffmpeg at all.
    try:
        import imageio_ffmpeg
        candidate = imageio_ffmpeg.get_ffmpeg_exe()
        if candidate and os.path.isfile(candidate):
            return candidate
    except Exception:
        pass

    return 'ffmpeg'


def is_ffmpeg_available() -> bool:
    """Check if ffmpeg is installed and runnable (PATH or winget packages folder)."""
    path = get_ffmpeg_path()
    try:
        result = subprocess.run([path, '-version'], capture_output=True, timeout=5, **_POPEN_KWARGS)
        return result.returncode == 0
    except Exception:
        return False


def is_winget_available() -> bool:
    """Check if winget (Windows Package Manager) is available."""
    try:
        result = subprocess.run(['winget', '--version'], capture_output=True, timeout=5, **_POPEN_KWARGS)
        return result.returncode == 0
    except Exception:
        return False
