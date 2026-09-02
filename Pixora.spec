"""Reproducible PyInstaller configuration for the Windows release."""

from pathlib import Path


project_root = Path(SPECPATH).resolve()

analysis = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=[(str(project_root / "app" / "resources"), "app/resources")],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

# Qt on Windows uses the ICU libraries supplied by the operating system.
# A developer PATH can contain an incompatible ICU build (for example from
# Poppler), which PyInstaller would otherwise collect into the application.
analysis.binaries = [
    entry
    for entry in analysis.binaries
    if not Path(entry[0]).name.lower().startswith("icu")
]

python_archive = PYZ(analysis.pure)

executable = EXE(
    python_archive,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="Pixora-v1.1.0-windows-x64",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / "app" / "resources" / "icons" / "pixora-icon.ico"),
)
