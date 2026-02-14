"""Application entry point."""
import sys
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw  # noqa: E402
from desktop_editor.app import DesktopEditorApp  # noqa: E402


def main():
    app = DesktopEditorApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
