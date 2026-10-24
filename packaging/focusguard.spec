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
        uac_admin=True,
        upx=False,
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
            "LSUIElement": True,
            "NSHighResolutionCapable": True,
            "NSAppleEventsUsageDescription": "FocusGuard reads your browser's current address to check whether you're on task.",
        },
    )
