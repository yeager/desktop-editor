"""Main application class."""
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, Gtk  # noqa: E402

from desktop_editor.i18n import _
from desktop_editor.window import DesktopEditorWindow


class DesktopEditorApp(Adw.Application):
    """The main GTK4/Adwaita application."""

    def __init__(self):
        super().__init__(
            application_id="se.danielnylander.desktop-editor",
            flags=Gio.ApplicationFlags.HANDLES_OPEN,
        )

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = DesktopEditorWindow(application=self)
        win.present()

    def do_open(self, files, n_files, hint):
        self.do_activate()
        win = self.props.active_window
        if files:
            win.open_file(files[0].get_path())

    def do_startup(self):
        Adw.Application.do_startup(self)
        self._setup_actions()

    def _setup_actions(self):
        for name, callback in [
            ("open", self._on_open),
            ("new", self._on_new),
            ("save", self._on_save),
            ("save-as", self._on_save_as),
            ("about", self._on_about),
            ("refresh", self._on_refresh_action),
            ("shortcuts", self._show_shortcuts_window),
            ("quit", self._on_quit),
        ]:
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            self.add_action(action)

        self.set_accels_for_action("app.open", ["<Control>o"])
        self.set_accels_for_action("app.new", ["<Control>n"])
        self.set_accels_for_action("app.save", ["<Control>s"])
        self.set_accels_for_action("app.save-as", ["<Control><Shift>s"])
        self.set_accels_for_action("app.quit", ["<Control>q"])
        self.set_accels_for_action("app.export", ["<Control>e"])

        export_action = Gio.SimpleAction.new("export", None)
        export_action.connect("activate", lambda *_: self.props.active_window and self.props.active_window._on_export_clicked())
        self.add_action(export_action)
        self.set_accels_for_action("app.refresh", ["F5"])
        self.set_accels_for_action("app.shortcuts", ["<Control>slash"])

    def _on_open(self, action, param):
        win = self.props.active_window
        if win:
            win.show_open_dialog()

    def _on_new(self, action, param):
        win = self.props.active_window
        if win:
            win.new_file()

    def _on_save(self, action, param):
        win = self.props.active_window
        if win:
            win.save_file()

    def _on_save_as(self, action, param):
        win = self.props.active_window
        if win:
            win.show_save_dialog()

    def _on_about(self, action, param):
        about = Adw.AboutDialog(
            application_name=_("Desktop File Editor"),
            application_icon="desktop-editor",
            developer_name="Daniel Nylander",
            version="0.2.1",
            developers=["Daniel Nylander <daniel@danielnylander.se>"],
            copyright="© 2026 Daniel Nylander",
            license_type=Gtk.License.GPL_3_0,
            website="https://github.com/yeager/desktop-editor",
            issue_url="https://github.com/yeager/desktop-editor/issues",
            translate_url="https://app.transifex.com/danielnylander/desktop-editor/",
            comments=_("Edit and translate .desktop files with ease"),
            translator_credits="Daniel Nylander <daniel@danielnylander.se>",
        )
        about.present(self.props.active_window)

    def _on_refresh_action(self, action, param):
        w = self.props.active_window
        if w and hasattr(w, '_load_into_ui'): w._load_into_ui()

    def _show_shortcuts_window(self, *_args):
        win = Gtk.ShortcutsWindow(transient_for=self.get_active_window(), modal=True)
        section = Gtk.ShortcutsSection(visible=True, max_height=10)
        group = Gtk.ShortcutsGroup(visible=True, title="General")
        for accel, title in [("<Control>q", "Quit"), ("F5", "Refresh"), ("<Control>slash", "Keyboard shortcuts"),
                             ("<Control>o", "Open"), ("<Control>s", "Save"), ("<Control>n", "New")]:
            s = Gtk.ShortcutsShortcut(visible=True, accelerator=accel, title=title)
            group.append(s)
        section.append(group)
        win.add_child(section)
        win.present()

    def _on_quit(self, action, param):
        self.quit()
