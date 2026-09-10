"""Keep release filenames and Windows metadata synchronized with the app."""

from pathlib import Path

from app import __version__


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_release_metadata_uses_application_version() -> None:
    release_filename = f"Pixora-v{__version__}-windows-x64.exe"
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    windows_metadata = (
        PROJECT_ROOT / "app" / "resources" / "windows-version-info.txt"
    ).read_text(encoding="utf-8")

    assert __version__ == "2.0.0"
    assert release_filename in readme
    assert release_filename in windows_metadata
    assert f"StringStruct('ProductVersion', '{__version__}')" in windows_metadata
