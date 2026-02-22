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

    # ── Welcome Dialog ───────────────────────────────────────

    def _show_welcome(self, win):
        dialog = Adw.Dialog()
        dialog.set_title(_("Welcome"))
        dialog.set_content_width(420)
        dialog.set_content_height(480)

        page = Adw.StatusPage()
        page.set_icon_name("text-editor-symbolic")
        page.set_title(_("Welcome to Desktop File Editor"))
        page.set_description(_(
            "Edit .desktop files with a visual interface.\n\n✓ Edit Name, Comment, Exec, Icon fields\n✓ Preview desktop entries\n✓ Validate against freedesktop spec\n✓ Manage translations"
        ))

        btn = Gtk.Button(label=_("Get Started"))
        btn.add_css_class("suggested-action")
        btn.add_css_class("pill")
        btn.set_halign(Gtk.Align.CENTER)
        btn.set_margin_top(12)
        btn.connect("clicked", self._on_welcome_close, dialog)
        page.set_child(btn)

        box = Adw.ToolbarView()
        hb = Adw.HeaderBar()
        hb.set_show_title(False)
        box.add_top_bar(hb)
        box.set_content(page)
        dialog.set_child(box)
        dialog.present(win)

    def _on_welcome_close(self, btn, dialog):
        self.settings["welcome_shown"] = True
        _save_settings(self.settings)
        dialog.close()

