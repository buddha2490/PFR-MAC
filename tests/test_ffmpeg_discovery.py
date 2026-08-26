"""
Tests for ffmpeg executable discovery (services/ffmpeg_utils.get_ffmpeg_path).

The macOS branches matter for packaging: a .app launched from Finder inherits a
minimal PATH that excludes /opt/homebrew/bin, and a recipient's Mac may have no
system ffmpeg at all — in which case the copy bundled into the frozen app is
the only one available.
"""

import glob as _glob
import os as _os
import shutil as _shutil
import sys

import pytest

from services import ffmpeg_utils

# Captured before any monkeypatching so helpers below can still reach the real
# implementations. ffmpeg_utils.os/glob/shutil ARE the stdlib modules, so
# patching an attribute on them is global for the duration of the test —
# re-importing inside a test would just hand back the patched version.
_REAL_ISFILE = _os.path.isfile
_REAL_GLOB = _glob.glob


@pytest.fixture
def no_system_ffmpeg(monkeypatch):
    """Hide every ffmpeg outside the frozen-app bundle.

    Only ffmpeg-looking paths are masked; unrelated isfile() calls (pytest's
    own, for instance) keep working.
    """
    monkeypatch.setattr(_shutil, 'which', lambda _: None)
    monkeypatch.delattr(sys, '_MEIPASS', raising=False)
    monkeypatch.setattr(
        _os.path, 'isfile',
        lambda p: False if 'ffmpeg' in str(p) else _REAL_ISFILE(p),
    )


def test_path_lookup_wins(monkeypatch):
    """An ffmpeg on PATH is preferred over every fallback."""
    monkeypatch.setattr(_shutil, 'which', lambda _: '/usr/bin/ffmpeg')
    assert ffmpeg_utils.get_ffmpeg_path() == '/usr/bin/ffmpeg'


def test_falls_back_to_bare_name(no_system_ffmpeg, monkeypatch):
    """With nothing found, callers still get something to exec (and a clear error)."""
    monkeypatch.setattr(_glob, 'glob', lambda *a, **k: [])
    assert ffmpeg_utils.get_ffmpeg_path() == 'ffmpeg'


@pytest.mark.skipif(sys.platform != 'darwin', reason="macOS prefix lookup")
def test_finds_homebrew_when_not_on_path(monkeypatch, no_system_ffmpeg):
    """A Finder-launched .app has no /opt/homebrew/bin on PATH; find it anyway."""
    monkeypatch.setattr(
        _os.path, 'isfile', lambda p: p == '/opt/homebrew/bin/ffmpeg')
    monkeypatch.setattr(_os, 'access', lambda p, m: True)
    assert ffmpeg_utils.get_ffmpeg_path() == '/opt/homebrew/bin/ffmpeg'


def _hide_system_ffmpeg(p):
    """Real isfile(), except the system ffmpeg prefixes report missing."""
    p = str(p)
    if p in ('/opt/homebrew/bin/ffmpeg', '/usr/local/bin/ffmpeg'):
        return False
    return _REAL_ISFILE(p)


def _make_bundle(tmp_path, mode):
    exe = tmp_path / 'imageio_ffmpeg' / 'binaries' / 'ffmpeg-macos-aarch64-v7.1'
    exe.parent.mkdir(parents=True)
    exe.write_text('#!/bin/sh\n')
    exe.chmod(mode)
    return exe


def test_finds_binary_bundled_in_frozen_app(monkeypatch, no_system_ffmpeg, tmp_path):
    """The frozen-app copy is found by path, not via imageio_ffmpeg.__file__.

    Guards the packaged build: PyInstaller puts the binary under
    sys._MEIPASS/imageio_ffmpeg/binaries/, and relying on imageio_ffmpeg's own
    __file__-based lookup surviving freezing is a needless dependency.
    """
    bundled = _make_bundle(tmp_path, 0o755)
    monkeypatch.setattr(sys, '_MEIPASS', str(tmp_path), raising=False)
    # Hide only the system prefixes, which are probed before the bundle; the
    # bundle's own path must still resolve.
    monkeypatch.setattr(_os.path, 'isfile', _hide_system_ffmpeg)

    assert ffmpeg_utils.get_ffmpeg_path() == str(bundled)


def test_ignores_non_executable_bundled_file(monkeypatch, no_system_ffmpeg, tmp_path):
    """A binary that lost its exec bit during packaging must not be returned."""
    bundled = _make_bundle(tmp_path, 0o644)
    monkeypatch.setattr(sys, '_MEIPASS', str(tmp_path), raising=False)
    monkeypatch.setattr(_os.path, 'isfile', _hide_system_ffmpeg)
    # imageio_ffmpeg is installed in the dev venv and would otherwise answer
    # after the bundle probe declines; this test is about the probe only.
    monkeypatch.setitem(sys.modules, 'imageio_ffmpeg', None)

    assert ffmpeg_utils.get_ffmpeg_path() != str(bundled)


def test_real_bundled_binary_matches_probe_pattern():
    """The shipped binary's name must match the glob the probe uses.

    A rename in imageio-ffmpeg would silently break timelapse on a machine with
    no system ffmpeg, which is exactly the packaged-app case.
    """
    imageio_ffmpeg = pytest.importorskip('imageio_ffmpeg')
    # Read the directory straight off the package rather than calling
    # get_ffmpeg_exe(), which caches its answer across tests.
    binaries_dir = _os.path.join(
        _os.path.dirname(imageio_ffmpeg.__file__), 'binaries')
    matches = [
        m for m in _REAL_GLOB(_os.path.join(binaries_dir, 'ffmpeg*'))
        if _os.access(m, _os.X_OK)
    ]
    assert matches, (
        f"no executable matching 'ffmpeg*' in {binaries_dir}; the frozen-app "
        "probe in services/ffmpeg_utils.get_ffmpeg_path() would find nothing"
    )
