"""
PyInstaller runtime hook: make cv2 importable inside a macOS .app bundle.

cv2's __init__.bootstrap() loads the native extension by putting the directory
that holds cv2.abi3.so onto sys.path and re-importing "cv2". It inserts that
path at index 0 only when it believes sys.path[0] is the package's parent;
otherwise it inserts at index 1.

A PyInstaller .app has two real copies of the package —
Contents/Frameworks/cv2 and Contents/Resources/cv2 — so cv2's realpath()-based
check compares two different directories, concludes the workaround is not
needed, and inserts at index 1. sys.path[0] then still points at a directory
containing a cv2 *package*, so the re-import returns __init__.py again and
bootstrap() raises:

    ERROR: recursion is detected during loading of "cv2" binary extensions.

sys.OpenCV_REPLACE_SYS_PATH_0 is cv2's own documented override; it forces the
insert to index 0 so the extension is found first. cv2 restores sys.path when
bootstrap() finishes, so nothing else is affected.

Only applies to frozen macOS builds; a normal source run is untouched.
"""

import sys

if sys.platform == 'darwin' and getattr(sys, 'frozen', False):
    sys.OpenCV_REPLACE_SYS_PATH_0 = True
