import json
import os

_DATA_DIR = os.path.join(os.path.expanduser('~'), '.pgsh')
_TOKEN_FILE = os.path.join(_DATA_DIR, 'token')
_DEVICES_FILE = os.path.join(_DATA_DIR, 'devices.json')


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
