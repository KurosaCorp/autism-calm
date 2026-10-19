# PyInstaller build recipe for Autism Calm (one-file, windowed .exe).
#
# Build (from the project root):
#     .venv\Scripts\python.exe -m pip install -r requirements-build.txt
#     .venv\Scripts\python.exe -m PyInstaller --noconfirm --clean AutismCalm.spec
# Output: dist\AutismCalm.exe
#
# This recipe also converts assets/logo.jpg into a multi-size .ico for the
# .exe and writes the Windows version info, so no other build steps are needed.

import sys
from pathlib import Path

from PIL import Image
from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo,
    StringFileInfo,
    StringStruct,
    StringTable,
    VarFileInfo,
    VarStruct,
    VSVersionInfo,
)

ROOT = Path(SPECPATH)
sys.path.insert(0, str(ROOT))
from calm import config  # noqa: E402  (app name/version; no Qt import)

ASSETS = ROOT / "assets"
AUDIO = ASSETS / "audio"
LOGO = ASSETS / "logo.jpg"
GENERATED = ROOT / "build" / "generated"
GENERATED.mkdir(parents=True, exist_ok=True)

# --- Check inputs ----------------------------------------------------------------
if not LOGO.is_file():
    raise SystemExit(f"Missing {LOGO}: put the app logo there before building.")
SKIP = {".standins"}
audio_files = [f for f in AUDIO.rglob("*") if f.is_file() and f.name not in SKIP and f.suffix != ".part"]
sound_files = [f for f in audio_files if f.suffix.lower() in config.SUPPORTED_EXTENSIONS]
if not sound_files:
    raise SystemExit(f"No sounds in {AUDIO}: run  python scripts/download_assets.py  first.")
print(f"Bundling {len(sound_files)} default sounds and the logo")

# --- Icon: logo.jpg -> multi-size .ico (centred on a transparent square) -----------
ICON = GENERATED / "AutismCalm.ico"
logo = Image.open(LOGO).convert("RGBA")
side = max(logo.size)
square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
square.paste(logo, ((side - logo.width) // 2, (side - logo.height) // 2))
square.save(ICON, sizes=[(s, s) for s in (16, 20, 24, 32, 40, 48, 64, 128, 256)])

# --- Windows version info (File Properties, Task Manager) ---------------------------
parts = tuple(int(p) for p in config.APP_VERSION.split(".")) + (0,)
VERSION_FILE = GENERATED / "version_info.txt"
VERSION_FILE.write_text(
    str(
        VSVersionInfo(
            ffi=FixedFileInfo(filevers=parts[:4], prodvers=parts[:4]),
            kids=[
                StringFileInfo(
                    [
                        StringTable(
                            "040904B0",
                            [
                                StringStruct("FileDescription", config.APP_NAME),
                                StringStruct("FileVersion", config.APP_VERSION),
                                StringStruct("InternalName", "AutismCalm"),
                                StringStruct("OriginalFilename", "AutismCalm.exe"),
                                StringStruct("ProductName", config.APP_NAME),
                                StringStruct("ProductVersion", config.APP_VERSION),
                            ],
                        )
                    ]
                ),
                VarFileInfo([VarStruct("Translation", [1033, 1200])]),
            ],
        )
    ),
    encoding="utf-8",
)

# --- Bundled data: lands in sys._MEIPASS/assets/... at runtime ----------------------
datas = [(str(LOGO), "assets")]
datas += [(str(f), str(Path("assets/audio") / f.parent.relative_to(AUDIO))) for f in audio_files]

# The OpenGL canvas is imported lazily (only when OpenGL works), so name it and
# the Qt OpenGL modules explicitly. The app uses no Qt 3D modules, so none are
# bundled (they would only add size).
hiddenimports = [
    "calm.visuals.render.gl_canvas",
    "PySide6.QtOpenGL",
    "PySide6.QtOpenGLWidgets",
]

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="AutismCalm",
    console=False,  # windowed: no terminal (same as --noconsole)
    icon=[str(ICON)],
    version=str(VERSION_FILE),
    upx=False,  # UPX-packed executables trigger more antivirus false positives
)
