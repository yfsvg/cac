# PyInstaller spec: a single FocusGuard.exe on Windows, FocusGuard.app on macOS.
# Build from the repo root with `pyinstaller packaging/focusguard.spec --noconfirm`; output goes to dist/.
import sys
import tomllib
from pathlib import Path

from PyInstaller.utils.hooks import collect_dynamic_libs

ROOT = Path(SPECPATH).parent
VERSION = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
WINDOWS = sys.platform == "win32"

a = Analysis(
    [str(ROOT / "packaging" / "launch.py")],
    pathex=[str(ROOT / "src")],
    # uiautomation loads these from its own bin/ folder at import time.
    binaries=collect_dynamic_libs("uiautomation") if WINDOWS else [],
    excludes=["tkinter"],
)
pyz = PYZ(a.pure)

if WINDOWS:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        name="FocusGuard",
        console=False,
        # Windows shows the UAC prompt before launching, and doesn't start the app if it's declined.
        uac_admin=True,
        upx=False,  # UPX-packed exes trip antivirus heuristics
    )
else:
    exe = EXE(pyz, a.scripts, exclude_binaries=True, name="FocusGuard", console=False)
    coll = COLLECT(exe, a.binaries, a.datas, name="FocusGuard")
    app = BUNDLE(
        coll,
        name="FocusGuard.app",
        bundle_identifier="com.focusguard.app",
        version=VERSION,
        info_plist={
            "CFBundleDisplayName": "FocusGuard",
            "LSUIElement": True,  # background app: no Dock icon
            "NSHighResolutionCapable": True,
            # Without this, macOS denies the AppleScript calls that read browser URLs instead of asking.
            "NSAppleEventsUsageDescription": "FocusGuard reads your browser's current address to check whether you're on task.",
        },
    )
