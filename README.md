# Desktop File Editor

A GTK4/Adwaita application for visually editing `.desktop` files with preview, validation, and translation management.

## Features

- Open/create `.desktop` files
- Visual editor for Name, Comment, Exec, Icon, Categories, etc.
- Preview: how the app looks in the app launcher
- View all translations (Name[sv], Comment[de], etc.)
- Add/remove translations per language
- Validation against freedesktop.org spec
- Warnings for missing icons, invalid Exec, etc.
- Browse /usr/share/applications/ and ~/.local/share/applications/

## Installation

### From .deb package

Download from [GitHub Releases](https://github.com/yeager/desktop-editor/releases).

### From source

```bash
pip install .
desktop-editor
```

## Requirements

- Python 3.10+
- GTK 4
- libadwaita

## License

GPL-3.0-or-later — Daniel Nylander <daniel@danielnylander.se>
