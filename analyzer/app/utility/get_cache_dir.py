import os
import sys
from pathlib import Path

def resolve_cache_dir() -> str:
    if os.getenv("IS_LOCAL", "false").lower() == "true":
        return os.getenv("HF_HOME")
    
    if getattr(sys, 'frozen', False):  # PyInstaller
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).parent

    hf_home = base_path / "app" / "cache"
    os.environ["HF_HOME"] = str(hf_home)
    return str(base_path / "app" / "cache")