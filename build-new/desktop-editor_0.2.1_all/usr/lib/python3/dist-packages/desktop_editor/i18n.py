"""Internationalization setup."""
import gettext
import locale
import os

APP_ID = "se.danielnylander.desktop-editor"
LOCALE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "po")

# Try system locale dir first, fall back to local
for d in ["/usr/share/locale", "/usr/local/share/locale", LOCALE_DIR]:
    if os.path.isdir(d):
        LOCALE_DIR = d
        break

try:
    locale.setlocale(locale.LC_ALL, "")
except locale.Error:
    pass

gettext.bindtextdomain("desktop-editor", LOCALE_DIR)
gettext.textdomain("desktop-editor")
_ = gettext.gettext
