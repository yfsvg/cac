import subprocess
import sys
import venv
from pathlib import Path

projectFolder = Path(__file__).resolve().parent.parent
envFolder = projectFolder / ".venv"
if sys.platform == "win32":
    envPython = envFolder / "Scripts" / "python.exe"
else:
    envPython = envFolder / "bin" / "python"
installedMarker = envFolder / "arete_installed.txt"
pyprojectFile = projectFolder / "pyproject.toml"


def needsInstall():
    if not installedMarker.exists():
        return True
    return installedMarker.read_text() != pyprojectFile.read_text()


if not envPython.exists():
    print("Setting up Arete for the first time, this takes a minute...")
    venv.create(envFolder, with_pip=True)

if needsInstall():
    print("Installing Arete's packages...")
    subprocess.run([str(envPython), "-m", "pip", "install", "--upgrade", "pip"], check=True)
    subprocess.run([str(envPython), "-m", "pip", "install", "-e", str(projectFolder)], check=True)
    installedMarker.write_text(pyprojectFile.read_text())
    print("All set!")
