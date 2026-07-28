# Logo + Icon Upgrade

## What changed
- `assets/ui/logo.png` — your logo, added to the project.
- `assets/ui/game_icon.ico` — multi-size (16–256px) icon version, generated from the same logo.
- `menu.py` — main menu now draws the real logo image instead of the old hand-drawn crest/title (falls back automatically to the old drawing if the file is ever missing).
- `main.py` — sets the game window/taskbar icon from `assets/ui/logo.png` via `pygame.display.set_icon(...)`.
- Added a **kill-combo multiplier**: chaining enemy kills within 1.2s builds a score multiplier (up to +100%), shown live in the HUD as `COMBO xN`.

## Install
Copy these into your project, keeping the folder structure:
```
galaxy_guardian/
├── assets/ui/logo.png
├── assets/ui/game_icon.ico
├── menu.py        (replace)
├── main.py        (replace)
└── hud.py         (replace)
```

## Setting the icon on the built .exe
The in-game window icon is automatic (via `pygame.display.set_icon`), but Windows also reads a
separate icon baked into the .exe itself. When you build with PyInstaller, point it at the `.ico`:

```bash
pyinstaller --onefile --windowed --icon=assets/ui/game_icon.ico --add-data "assets;assets" main.py
```

That's it — the taskbar, window title bar, and the .exe file icon will all match.