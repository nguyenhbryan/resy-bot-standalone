from os import environ
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]


def load_backend_env() -> None:
    env_path = BACKEND_DIR / ".env"

    try:
        from dotenv import load_dotenv
    except ImportError:
        _load_env_file(env_path)
        return

    load_dotenv(env_path)


def _load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return

    for line in env_path.read_text().splitlines():
        line = line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        environ.setdefault(key.strip(), value.strip().strip("\"'"))
