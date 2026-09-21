# app/models/swift_validator.py
import os, sys, json, re
from pathlib import Path

_SWIFT_CODES: set[str] | None = None
_SWIFT_PATTERN = re.compile(r"^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$")

def _swift_data_dirs(explicit: str | None = None) -> list[Path]:
    """Order of precedence:
       1) explicit arg
       2) SWIFT_DATA_DIR env
       3) (if not IS_LOCAL) PyInstaller _MEIPASS
       4) common dev/image paths
    """
    is_local = os.getenv("IS_LOCAL", "false").strip().lower() == "true"
    cands: list[Path] = []

    # 1) explicit override
    if explicit:
        cands.append(Path(explicit))

    # 2) env override
    env = os.getenv("SWIFT_DATA_DIR")
    if env:
        cands.append(Path(env))

    # 3) only use _MEIPASS when NOT local
    if not is_local and getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        cands.append(Path(sys._MEIPASS) / "swift_library")
        # fallback variant if you ever bundled differently
        cands.append(Path(sys._MEIPASS) / "app" / "swift_library")

    # 4) dev / image paths
    here = Path(__file__).resolve()
    cands += [
        here.parent / "swift_library",                          # repo layout
        here.parent,                                            # if this file lives inside swift_library
        Path.cwd() / "swift_library",                           # run from project root
        Path.cwd() / "app" / "swift_library",                   # run from /app
        Path("/app/swift_library"),                             # final image sidecar copy
    ]

    # dedupe preserving order
    seen, out = set(), []
    for p in cands:
        if p not in seen:
            seen.add(p); out.append(p)
    return out

def _load_swift_dataset(results_dir: str | None = None) -> None:
    global _SWIFT_CODES
    if _SWIFT_CODES is not None:
        return

    _SWIFT_CODES = set()
    for d in _swift_data_dirs(results_dir):
        if not d.exists():
            continue
        loaded = False
        for f in d.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            for row in data:
                code = str(row.get("swift_code", "")).strip().upper()
                if code:
                    _SWIFT_CODES.add(code)
                    if len(code) >= 8:
                        _SWIFT_CODES.add(code[:8])
                    loaded = True
        if loaded:
            # swap to your logger if you prefer
            print(f"[swift] loaded {len(_SWIFT_CODES)} codes from {d}")
            break

def validate_swift(swift_code: str) -> bool:
    if not swift_code:
        return False
    code = swift_code.strip().upper()
    if not _SWIFT_PATTERN.match(code):
        return False

    _load_swift_dataset()

    # strict: require dataset present
    if not _SWIFT_CODES:
        return False

    return code in _SWIFT_CODES or code[:8] in _SWIFT_CODES
