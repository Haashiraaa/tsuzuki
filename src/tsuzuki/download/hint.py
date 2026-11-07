"""OS-aware advice for installing aria2c."""

import platform

_HINTS = {
    "Linux": "sudo apt install aria2 | sudo pacman -S aria2 | sudo dnf install aria2",
    "Darwin": "brew install aria2",
    "Windows": "winget install aria2.aria2 | choco install aria2",
}
_DEFAULT = "see https://aria2.github.io/ for install instructions"


def aria2_install_hint(system: str | None = None) -> str:
    return _HINTS.get(system or platform.system(), _DEFAULT)
