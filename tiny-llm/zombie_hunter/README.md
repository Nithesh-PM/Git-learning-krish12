# Zombie Hunter: Last Light

A top-down survival shooter that runs directly in a modern web browser. The game draws its city, characters, enemies, ammunition, and effects on an HTML Canvas; it needs no downloads, accounts, server, or external art.

## Play in a browser

1. Open the `zombie_hunter` folder in File Explorer or VS Code.
2. Double-click `index.html` to open the game in your browser.
3. Select **Start Game**. In VS Code, you can alternatively open `index.html` with the Live Server extension.

No Python, Pygame, package installation, or internet connection is required to play.

## Controls

| Action | Control |
| --- | --- |
| Move | WASD or arrow keys |
| Aim | Mouse |
| Fire | Hold left mouse button |
| Reload | R |
| Pause / resume | Escape to pause; P or Enter to resume |
| Start | Enter or Space from the title or instructions |
| Restart | Enter or R after game over |

Select **Start Game**, **Instructions**, or **Quit** on the title screen. (Browsers do not let a page close its own tab; **Quit** displays a close-tab message.) Zombies chase and attack the player, with faster arrivals and tougher types as time passes. Green supply cases restore reserve ammunition; defeating every fifth zombie also drops ammo. A new game starts with 12 rounds loaded and 72 in reserve.

## Project files

```text
zombie_hunter/
├── index.html       Browser entry point
├── style.css        Responsive page styling
├── game.js          Canvas rendering, game loop, controls, and gameplay
├── main.py          Original Python/Pygame version
├── requirements.txt Python version dependency
├── README.md
└── assets/          Reserved for optional art and sound assets
```

The browser game uses plain JavaScript and the Canvas API; `requirements.txt` applies only to the retained Python version. To run that separate version, install Pygame with `python -m pip install -r requirements.txt` and launch `python main.py`.
