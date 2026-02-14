"""Parser and model for .desktop files (freedesktop.org Desktop Entry spec)."""
import os
import re
from collections import OrderedDict
from typing import Optional

from desktop_editor.i18n import _

# Keys defined in the spec
STANDARD_KEYS = {
    "Type", "Version", "Name", "GenericName", "NoDisplay", "Comment",
    "Icon", "Hidden", "OnlyShowIn", "NotShowIn", "DBusActivatable",
    "TryExec", "Exec", "Path", "Terminal", "Actions", "MimeType",
    "Categories", "Implements", "Keywords", "StartupNotify",
    "StartupWMClass", "URL", "PrefersNonDefaultGPU", "SingleMainWindow",
}

REQUIRED_KEYS = {"Type", "Name"}

VALID_TYPES = {"Application", "Link", "Directory"}

# freedesktop.org main categories
MAIN_CATEGORIES = [
    "AudioVideo", "Audio", "Video", "Development", "Education", "Game",
    "Graphics", "Network", "Office", "Science", "Settings", "System",
    "Utility",
]

LOCALE_KEY_RE = re.compile(r"^([A-Za-z]+)\[([a-zA-Z_@.]+)\]$")


class ValidationMessage:
    """A validation warning or error."""
    def __init__(self, level: str, message: str):
        self.level = level  # "error" or "warning"
        self.message = message

    def __repr__(self):
        return f"[{self.level.upper()}] {self.message}"


class DesktopFile:
    """Represents a parsed .desktop file."""

    def __init__(self):
        self.path: Optional[str] = None
        # Main group entries: key -> value
        self.entries: OrderedDict[str, str] = OrderedDict()
        # Localized entries: (key, locale) -> value
        self.localized: dict[tuple[str, str], str] = {}
        # Extra groups (actions, etc.): group_name -> OrderedDict
        self.extra_groups: OrderedDict[str, OrderedDict] = OrderedDict()

    @classmethod
    def new_application(cls) -> "DesktopFile":
        """Create a blank Application .desktop file."""
        df = cls()
        df.entries["Type"] = "Application"
        df.entries["Name"] = ""
        df.entries["Comment"] = ""
        df.entries["Exec"] = ""
        df.entries["Icon"] = ""
        df.entries["Categories"] = ""
        df.entries["Terminal"] = "false"
        return df

    @classmethod
    def load(cls, path: str) -> "DesktopFile":
        """Parse a .desktop file from disk."""
        df = cls()
        df.path = path
        current_group = None

        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.rstrip("\n\r")
                if not line or line.startswith("#"):
                    continue
                if line.startswith("[") and line.endswith("]"):
                    current_group = line[1:-1]
                    if current_group != "Desktop Entry":
                        df.extra_groups.setdefault(current_group, OrderedDict())
                    continue
                if "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()

                m = LOCALE_KEY_RE.match(key)
                if current_group == "Desktop Entry" or current_group is None:
                    if m:
                        df.localized[(m.group(1), m.group(2))] = value
                    else:
                        df.entries[key] = value
                elif current_group in df.extra_groups:
                    df.extra_groups[current_group][key] = value

        return df

    def save(self, path: Optional[str] = None):
        """Write .desktop file to disk."""
        path = path or self.path
        if not path:
            raise ValueError(_("No file path specified"))
        self.path = path

        lines = ["[Desktop Entry]\n"]
        for key, value in self.entries.items():
            lines.append(f"{key}={value}\n")
            # Write localized versions right after the base key
            for (lkey, locale), lvalue in sorted(self.localized.items()):
                if lkey == key:
                    lines.append(f"{lkey}[{locale}]={lvalue}\n")

        for group_name, group_entries in self.extra_groups.items():
            lines.append(f"\n[{group_name}]\n")
            for key, value in group_entries.items():
                lines.append(f"{key}={value}\n")

        with open(path, "w", encoding="utf-8") as f:
            f.writelines(lines)

    def get_locales(self) -> list[str]:
        """Return sorted list of all locales used."""
        locales = set()
        for _, locale in self.localized:
            locales.add(locale)
        return sorted(locales)

    def get_translations(self, key: str) -> dict[str, str]:
        """Return {locale: value} for a given key."""
        result = {}
        for (k, locale), value in self.localized.items():
            if k == key:
                result[locale] = value
        return result

    def set_translation(self, key: str, locale: str, value: str):
        self.localized[(key, locale)] = value

    def remove_translation(self, key: str, locale: str):
        self.localized.pop((key, locale), None)

    def remove_locale(self, locale: str):
        to_remove = [(k, l) for k, l in self.localized if l == locale]
        for key in to_remove:
            del self.localized[key]

    def validate(self) -> list[ValidationMessage]:
        """Validate against freedesktop.org spec."""
        msgs = []

        # Required keys
        for key in REQUIRED_KEYS:
            if key not in self.entries or not self.entries[key]:
                msgs.append(ValidationMessage("error", _("Missing required key: %s") % key))

        # Type check
        dtype = self.entries.get("Type", "")
        if dtype and dtype not in VALID_TYPES:
            msgs.append(ValidationMessage("error", _("Invalid Type: %s") % dtype))

        # Exec check for Application
        if dtype == "Application":
            if not self.entries.get("Exec"):
                msgs.append(ValidationMessage("warning", _("Application type should have an Exec key")))

        # URL check for Link
        if dtype == "Link":
            if not self.entries.get("URL"):
                msgs.append(ValidationMessage("warning", _("Link type should have a URL key")))

        # Icon warning
        if not self.entries.get("Icon"):
            msgs.append(ValidationMessage("warning", _("No icon specified")))

        # Categories warning
        if dtype == "Application" and not self.entries.get("Categories"):
            msgs.append(ValidationMessage("warning", _("No categories specified")))

        # Check for unknown keys
        for key in self.entries:
            if key not in STANDARD_KEYS and not key.startswith("X-"):
                msgs.append(ValidationMessage("warning", _("Non-standard key: %s") % key))

        return msgs


def list_desktop_files() -> list[str]:
    """List .desktop files from standard locations."""
    dirs = [
        "/usr/share/applications",
        "/usr/local/share/applications",
        os.path.expanduser("~/.local/share/applications"),
    ]
    files = []
    for d in dirs:
        if os.path.isdir(d):
            for entry in sorted(os.listdir(d)):
                if entry.endswith(".desktop"):
                    files.append(os.path.join(d, entry))
    return files
