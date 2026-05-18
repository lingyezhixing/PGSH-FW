import json
import os

_DATA_DIR = os.environ.get('FLET_APP_STORAGE_DATA') or os.path.join(os.path.expanduser('~'), '.pgsh')
_TOKEN_FILE = os.path.join(_DATA_DIR, 'token')
_DEVICES_FILE = os.path.join(_DATA_DIR, 'devices.json')
_ALIASES_FILE = os.path.join(_DATA_DIR, 'aliases.json')


def _ensure_dir():
    os.makedirs(_DATA_DIR, exist_ok=True)


def load_token() -> str | None:
    if not os.path.exists(_TOKEN_FILE):
        return None
    return open(_TOKEN_FILE, encoding='utf-8').read().strip() or None


def save_token(token: str):
    _ensure_dir()
    with open(_TOKEN_FILE, 'w', encoding='utf-8') as f:
        f.write(token)


def load_devices() -> list[dict]:
    if not os.path.exists(_DEVICES_FILE):
        return []
    with open(_DEVICES_FILE, encoding='utf-8') as f:
        return json.load(f)


def save_devices(devices: list[dict]):
    _ensure_dir()
    with open(_DEVICES_FILE, 'w', encoding='utf-8') as f:
        json.dump(devices, f, ensure_ascii=False, indent=2)


def load_aliases() -> dict[str, str]:
    if not os.path.exists(_ALIASES_FILE):
        return {}
    with open(_ALIASES_FILE, encoding='utf-8') as f:
        return json.load(f)


def save_aliases(aliases: dict[str, str]):
    _ensure_dir()
    with open(_ALIASES_FILE, 'w', encoding='utf-8') as f:
        json.dump(aliases, f, ensure_ascii=False, indent=2)
