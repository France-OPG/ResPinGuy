#!/usr/bin/env python3
"""Fonctions communes à l'interface graphique ResPinGuy."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk  # noqa: E402

APP_ID = "fr.fopg.respinguy"
APP_NAME = "ResPinGuy"

FILE_DIR = Path(os.environ.get("RPG_FILE_DIR", "/usr/share/ResPinGuy-File"))
CONF_DIR = Path(os.environ.get("RPG_CONF_DIR", "/usr/share/ResPinGuy-File-Config"))
CONF_FILE = CONF_DIR / "respinguy-config"
CONF_LOCAL = CONF_DIR / "respinguy-config.local"
INSTALLER = FILE_DIR / "respinguy-install"
BUILD_SCRIPT = FILE_DIR / "respinguy-build"

LANG_NAMES = {
    "fr": "Français",
    "en": "English",
    "es": "Español",
    "de": "Deutsch",
    "pt": "Português",
}

COLORS = {
    "bg": "#141414",
    "yellow": "#ffb516",
    "blue": "#1d2f52",
    "green": "#73ba25",
    "red": "#ee0000",
}

CSS = """
window, dialog, messagedialog, .background {
    background-image: none; background-color: #141414; color: #ffb516;
}
window > box, window > grid, notebook, notebook > stack, notebook > stack > box,
notebook > stack > box > box, notebook > stack > scrolledwindow,
notebook > stack > scrolledwindow > viewport, notebook > stack > viewport,
notebook > stack > viewport > box, viewport, viewport > box, grid {
    background-image: none; background-color: #141414;
}
headerbar { background-image: none; background-color: #141414; color: #ffb516;
            border-bottom: 2px solid #1d2f52; box-shadow: none; }
headerbar .title { color: #ffb516; font-weight: bold; }
label, check, radio { color: #ffb516; }
button { background-image: none; background-color: #1d2f52; color: #ffb516;
         border: 1px solid #1d2f52; border-radius: 4px; padding: 6px 14px; }
button label { color: #ffb516; }
button:hover { background-image: none; background-color: #73ba25; color: #141414; }
button:hover label { color: #141414; }
button:active { background-image: none; background-color: #5a941d; color: #141414; }
button:active label { color: #141414; }
button.suggested-action { background-image: none; background-color: #73ba25; color: #141414; }
button.suggested-action label { color: #141414; }
button.destructive-action { background-image: none; background-color: #ee0000; color: #ffffff; }
button.destructive-action label { color: #ffffff; }
button:disabled { background-image: none; background-color: #111111; color: #6b5a1c; }
button:disabled label { color: #6b5a1c; }
entry, spinbutton, combobox button { background-image: none; background-color: #141414;
        color: #ffb516; border: 1px solid #1d2f52; border-radius: 4px; }
entry:focus, combobox button:focus { border-color: #73ba25; }
entry:disabled { background-image: none; background-color: #101010; color: #6b5a1c; }
combobox window, menu, .menu { background-image: none; background-color: #141414; color: #ffb516; }
menuitem:hover { background-image: none; background-color: #73ba25; color: #141414; }
notebook { background-image: none; background-color: #141414; }
notebook tab { background-image: none; background-color: #141414; color: #ffb516; padding: 8px 18px; }
notebook tab:checked { background-image: none; background-color: #1d2f52; color: #ffb516; }
frame > border { border: 1px solid #1d2f52; }
scrolledwindow { border: 1px solid #1d2f52; background-image: none; background-color: #141414; }
scrolledwindow > viewport { background-image: none; background-color: #141414; }
textview, textview text { background-image: none; background-color: #141414; color: #ffb516; }
progressbar trough { background-image: none; background-color: #1d2f52; border-radius: 4px; }
progressbar progress { background-image: none; background-color: #73ba25; border-radius: 4px; }
assistant .sidebar { background-image: none; background-color: #141414; color: #ffb516; }
assistant .sidebar label { color: #ffb516; }
.dim-label { color: #b98b18; }
.error-label { color: #ee0000; }
.success-label { color: #73ba25; }
"""


def read_version() -> str:
    try:
        text = (FILE_DIR / "VERSION").read_text(encoding="utf-8").strip()
        return text or "0.44"
    except OSError:
        return "0.44"


def is_live() -> bool:
    """Vrai si le système courant est le live ResPinGuy."""
    try:
        cmdline = Path("/proc/cmdline").read_text(encoding="utf-8", errors="ignore")
        if "root=live:" in cmdline or "rd.live.image" in cmdline:
            return True
    except OSError:
        pass
    return Path("/run/initramfs/live/LiveOS/squashfs.img").is_file()


def live_dir() -> Path | None:
    for path in ("/run/initramfs/live", "/run/initramfs/livedev", "/mnt/live"):
        base = Path(path)
        if (base / "LiveOS/squashfs.img").is_file():
            return base
    try:
        for line in Path("/proc/mounts").read_text(encoding="utf-8", errors="ignore").splitlines():
            parts = line.split()
            if len(parts) >= 2 and (Path(parts[1]) / "LiveOS/squashfs.img").is_file():
                return Path(parts[1])
    except OSError:
        pass
    return None


def apply_theme() -> None:
    settings = Gtk.Settings.get_default()
    if settings:
        settings.set_property("gtk-application-prefer-dark-theme", True)
    screen = Gdk.Screen.get_default()
    if not screen:
        return
    provider = Gtk.CssProvider()
    provider.load_from_data(CSS.encode("utf-8"))
    Gtk.StyleContext.add_provider_for_screen(
        screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
    )


def elevated_prefix() -> list[str]:
    """Commande d'élévation : sudo sans mot de passe, sinon pkexec."""
    if sudo_available():
        return ["sudo", "-n"]
    if shutil.which("pkexec"):
        return ["pkexec"]
    return []


def elevated_available() -> bool:
    return bool(sudo_available() or shutil.which("pkexec"))


def sudo_available() -> bool:
    if not shutil.which("sudo"):
        return False
    try:
        return subprocess.run(
            ["sudo", "-n", "true"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        ).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def run_capture(cmd: list[str], timeout: int = 10) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            errors="replace",
        )
        return proc.returncode, proc.stdout, proc.stderr
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, "", str(exc)


def read_config() -> dict[str, str]:
    script = r"""
. "$1" >/dev/null 2>&1
printf '%s\0' \
  "${RPGBUILDNAME-}" "${RPGHOME-}" "${KERNEL-}" "${ARCH-}" "${VMLINUZ-}" \
  "${ROOTDIR-}" "${RPGCONFIGUSER-}" "${RPGCONFIGUSERPERS-}" "${HOME-}" "${RPG_LANG-}"
"""
    rc, out, err = run_capture(["bash", "-c", script, "bash", str(CONF_FILE)])
    values = out.split("\0")
    if rc != 0 or len(values) < 10:
        raise RuntimeError(err.strip() or "Impossible de lire la configuration.")
    keys = [
        "name", "out", "kernel", "arch", "vmlinuz", "rootdir",
        "config_user", "config_pers", "home", "lang",
    ]
    cfg = dict(zip(keys, values[:10]))
    if cfg["config_pers"]:
        cfg["mode"] = "pers"
    elif cfg["config_user"]:
        cfg["mode"] = "iso"
    else:
        cfg["mode"] = "none"
    if cfg["mode"] == "none":
        cfg["home"] = ""
    if cfg["lang"] not in LANG_NAMES:
        cfg["lang"] = "fr"
    return cfg


def _shell_quote(value: str) -> str:
    return shlex.quote(value or "")


def write_config(cfg: dict[str, str]) -> None:
    lines = [
        "# ResPinGuy - réglages de l'interface graphique",
        "# Ce fichier est prioritaire sur respinguy-config.",
        "# Le supprimer rétablit les valeurs par défaut.",
        "",
        f"RPGBUILDNAME={_shell_quote(cfg.get('name', ''))}",
        f"RPGHOME={_shell_quote(cfg.get('out', ''))}",
        f"RPG_LANG={_shell_quote(cfg.get('lang', 'fr'))}",
    ]
    mode = cfg.get("mode", "none")
    if mode == "iso":
        lines.append("RPGCONFIGUSER=1")
    elif mode == "pers":
        lines.append("RPGCONFIGUSERPERS=1")
    if mode != "none" and cfg.get("home"):
        lines.append(f"HOME={_shell_quote(cfg['home'])}")
    for key, var in (("kernel", "KERNEL"), ("vmlinuz", "VMLINUZ"), ("rootdir", "ROOTDIR")):
        value = cfg.get(key, "").strip()
        if value:
            lines.append(f"{var}={_shell_quote(value)}")
    data = "\n".join(lines) + "\n"

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)
    try:
        rc, _, err = run_capture(["bash", "-n", str(tmp_path)])
        if rc != 0:
            raise RuntimeError(f"Configuration invalide : {err}")
        write_root_file(CONF_LOCAL, data)
    finally:
        tmp_path.unlink(missing_ok=True)


def write_root_file(path: Path, data: str) -> None:
    path = Path(path)
    if path.exists() and os.access(path, os.W_OK):
        path.write_text(data, encoding="utf-8")
        return
    if not path.exists() and os.access(path.parent, os.W_OK):
        path.write_text(data, encoding="utf-8")
        return

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)
    try:
        prefix = elevated_prefix()
        if not prefix:
            raise RuntimeError("sudo/pkexec est introuvable : impossible d'écrire la configuration.")
        proc = subprocess.run(
            prefix + ["cp", str(tmp_path), str(path)],
            capture_output=True,
            text=True,
            errors="replace",
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or "Échec de l'écriture (élévation).")
        subprocess.run(prefix + ["chmod", "644", str(path)], capture_output=True)
    finally:
        tmp_path.unlink(missing_ok=True)


def list_disks() -> tuple[list[dict], str]:
    rc, out, err = run_capture(
        ["lsblk", "-J", "-dpno", "NAME,SIZE,MODEL,TYPE"], timeout=15
    )
    rows: list[dict] = []
    if rc == 0:
        try:
            data = json.loads(out)
            for dev in data.get("blockdevices", []):
                rows.append({
                    "name": dev.get("name") or "",
                    "size": (dev.get("size") or "").strip(),
                    "model": (dev.get("model") or "").strip(),
                    "type": dev.get("type") or "",
                })
        except json.JSONDecodeError:
            rows = []
    if not rows:
        # Anciennes versions de lsblk : sortie texte
        rc, out, err = run_capture(
            ["lsblk", "-dpno", "NAME,SIZE,MODEL,TYPE"], timeout=15
        )
        if rc != 0:
            raise RuntimeError(err.strip() or "lsblk a échoué.")
        for line in out.splitlines():
            parts = line.split(None, 3)
            if len(parts) < 2:
                continue
            rest = parts[3].split() if len(parts) > 3 else []
            rows.append({
                "name": parts[0],
                "size": parts[1],
                "model": " ".join(rest[:-1]),
                "type": rest[-1] if rest else "",
            })

    live = live_disk()
    disks = []
    for dev in rows:
        name = dev.get("name") or ""
        dtype = dev.get("type") or ""
        if not name.startswith("/dev/") or (dtype and dtype != "disk"):
            continue
        if any(name.startswith(p) for p in (
            "/dev/loop", "/dev/sr", "/dev/zram", "/dev/ram", "/dev/dm-", "/dev/md"
        )):
            continue
        if live and name == live:
            continue
        disks.append({
            "name": name,
            "size": (dev.get("size") or "").strip(),
            "model": (dev.get("model") or "").strip(),
        })
    disks.sort(key=lambda d: d["name"])
    return disks, live or ""


def live_disk() -> str:
    base = live_dir()
    if not base:
        return ""
    rc, out, _ = run_capture(["findmnt", "-n", "-o", "SOURCE", str(base)])
    source = out.strip().splitlines()[0] if rc == 0 and out.strip() else ""
    if not source:
        try:
            for line in Path("/proc/mounts").read_text(encoding="utf-8", errors="ignore").splitlines():
                parts = line.split()
                if len(parts) >= 2 and parts[1] == str(base):
                    source = parts[0]
                    break
        except OSError:
            pass
    if not source.startswith("/dev/"):
        return ""
    rc, out, _ = run_capture(["lsblk", "-n", "-o", "PKNAME", source])
    pk = out.strip().splitlines()[0] if rc == 0 and out.strip() else ""
    return f"/dev/{pk}" if pk else source


def tail_text(path: Path, lines: int = 200) -> str:
    try:
        path = Path(path)
        size = path.stat().st_size
        with path.open("rb") as fh:
            if size > 256 * 1024:
                fh.seek(size - 256 * 1024)
            data = fh.read()
        content = data.decode("utf-8", errors="replace")
    except OSError:
        return ""
    return "\n".join(content.splitlines()[-lines:])


def show_error(parent, title: str, text: str) -> None:
    dialog = Gtk.MessageDialog(
        transient_for=parent,
        modal=True,
        message_type=Gtk.MessageType.ERROR,
        buttons=Gtk.ButtonsType.CLOSE,
        text=title,
    )
    dialog.format_secondary_text(text)
    dialog.run()
    dialog.destroy()


def show_info(parent, title: str, text: str) -> None:
    dialog = Gtk.MessageDialog(
        transient_for=parent,
        modal=True,
        message_type=Gtk.MessageType.INFO,
        buttons=Gtk.ButtonsType.CLOSE,
        text=title,
    )
    dialog.format_secondary_text(text)
    dialog.run()
    dialog.destroy()


def show_text(parent, title: str, text: str) -> None:
    dialog = Gtk.Dialog(title=title, transient_for=parent, modal=True)
    dialog.set_default_size(900, 560)
    dialog.add_button("Fermer", Gtk.ResponseType.CLOSE)
    area = dialog.get_content_area()
    view = Gtk.TextView()
    view.set_editable(False)
    view.set_monospace(True)
    view.get_buffer().set_text(text or "(journal vide)")
    scrolled = Gtk.ScrolledWindow()
    scrolled.set_hexpand(True)
    scrolled.set_vexpand(True)
    scrolled.add(view)
    area.pack_start(scrolled, True, True, 0)
    dialog.show_all()
    dialog.run()
    dialog.destroy()


def open_log(parent, title: str, path: Path) -> None:
    show_text(parent, title, tail_text(path, 2000))
