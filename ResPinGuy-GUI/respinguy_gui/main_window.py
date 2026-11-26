#!/usr/bin/env python3
"""Fenêtre principale de ResPinGuy (configuration et build)."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # noqa: E402

from . import common  # noqa: E402


class ProcessDialog(Gtk.Dialog):
    """Affiche la sortie d'une commande longue sans bloquer l'interface."""

    def __init__(self, parent, title: str, cmd: list[str], env: dict | None = None,
                 on_done=None):
        super().__init__(title=title, transient_for=parent, modal=True)
        self.set_default_size(900, 560)
        self.close_button = self.add_button("Fermer", Gtk.ResponseType.CLOSE)
        self.close_button.set_sensitive(False)
        self.connect("delete-event", self._on_delete)
        self.on_done = on_done
        self.rc: int | None = None
        self.log_path = Path(f"/tmp/respinguy-gui-tool-{os.getpid()}-{int(time.time())}.log")
        self.log_text = ""
        self._fh = open(self.log_path, "wb")
        child_env = os.environ.copy()
        if env:
            child_env.update(env)
        try:
            self.proc = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=self._fh,
                stderr=subprocess.STDOUT,
                env=child_env,
                close_fds=True,
            )
        except OSError as exc:
            self._fh.close()
            common.show_error(parent, title, str(exc))
            self.rc = 1
            self.proc = None

        area = self.get_content_area()
        self.progress = Gtk.ProgressBar()
        self.progress.set_pulse_step(0.08)
        area.pack_start(self.progress, False, False, 0)
        self.status = Gtk.Label(label="En cours...", xalign=0)
        area.pack_start(self.status, False, False, 0)
        view = Gtk.TextView()
        view.set_editable(False)
        view.set_monospace(True)
        self.buffer = view.get_buffer()
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)
        scrolled.add(view)
        area.pack_start(scrolled, True, True, 0)
        self.show_all()
        if self.proc is not None:
            GLib.timeout_add(250, self._poll)
        else:
            self._finish()

    def _poll(self) -> bool:
        if self.proc is None:
            return False
        self.progress.pulse()
        text = common.tail_text(self.log_path, 200)
        if text != self.log_text:
            self.log_text = text
            self.buffer.set_text(text)
        if self.proc.poll() is None:
            return True
        self.rc = self.proc.returncode
        self._finish()
        return False

    def _finish(self):
        try:
            self._fh.close()
        except OSError:
            pass
        self.close_button.set_sensitive(True)
        self.progress.set_fraction(1.0)
        if self.rc == 0:
            self.status.set_markup("<span foreground='#73ba25'>Terminé.</span>")
        else:
            self.status.set_markup(f"<span foreground='#ee0000'>Échec (code {self.rc}).</span>")
        if self.on_done:
            self.on_done(self.rc, self.log_path)

    def _on_delete(self, *_args):
        if self.proc is not None and self.proc.poll() is None:
            return True
        return False


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, app=None):
        super().__init__(application=app) if app else super().__init__()
        self.set_title(f"ResPinGuy {common.read_version()}")
        self.set_default_size(960, 700)
        self.set_icon_name("respinguy")

        self.build_proc: subprocess.Popen | None = None
        self.build_log: Path | None = None
        self.build_status: Path | None = None
        self.build_log_text = ""
        self.build_running = False
        self.build_fh = None
        self.connect("delete-event", self._on_delete)

        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.props.title = "ResPinGuy"
        header.props.subtitle = f"Version {common.read_version()}"
        self.set_titlebar(header)

        notebook = Gtk.Notebook()
        notebook.append_page(self._build_config_page(), Gtk.Label(label="Configuration"))
        notebook.append_page(self._build_build_page(), Gtk.Label(label="Image ISO"))
        notebook.append_page(self._build_tools_page(), Gtk.Label(label="Outils"))
        self.add(notebook)

        self.show_all()
        self.load_config()
        self._refresh_summary()

    # ------------------------------------------------------------------ config

    def _build_config_page(self) -> Gtk.Widget:
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        outer.set_border_width(24)

        intro = Gtk.Label(xalign=0)
        intro.set_markup(
            "<span size='large' weight='bold'>Configuration de l'image</span>\n"
            "Ces réglages sont enregistrés dans respinguy-config.local."
        )
        intro.set_line_wrap(True)
        outer.pack_start(intro, False, False, 0)

        grid = Gtk.Grid(column_spacing=14, row_spacing=10)
        grid.set_hexpand(True)

        def add_row(row: int, label: str, widget: Gtk.Widget):
            lab = Gtk.Label(label=label, xalign=0)
            grid.attach(lab, 0, row, 1, 1)
            grid.attach(widget, 1, row, 1, 1)

        self.name_entry = Gtk.Entry()
        self.name_entry.set_hexpand(True)
        add_row(0, "Nom de l'image", self.name_entry)

        self.out_entry = Gtk.Entry()
        self.out_entry.set_hexpand(True)
        add_row(1, "Dossier de destination", self.out_entry)

        self.kernel_entry = Gtk.Entry()
        self.kernel_entry.set_hexpand(True)
        self.kernel_entry.set_placeholder_text("auto (uname -r)")
        add_row(2, "Version du noyau", self.kernel_entry)

        self.vmlinuz_entry = Gtk.Entry()
        self.vmlinuz_entry.set_hexpand(True)
        self.vmlinuz_entry.set_placeholder_text("auto (/boot/vmlinuz-…)")
        add_row(3, "Image du noyau", self.vmlinuz_entry)

        self.arch_label = Gtk.Label(xalign=0)
        add_row(4, "Architecture", self.arch_label)

        self.rootdir_entry = Gtk.Entry()
        self.rootdir_entry.set_hexpand(True)
        add_row(5, "Dossiers inclus", self.rootdir_entry)

        self.mode_combo = Gtk.ComboBoxText()
        self.mode_combo.append("none", "Aucun (image système seulement)")
        self.mode_combo.append("iso", "Inclure /home (ISO)")
        self.mode_combo.append("pers", "Inclure /home (persistance)")
        self.mode_combo.connect("changed", self._on_mode_changed)
        add_row(6, "Contenu utilisateur", self.mode_combo)

        self.home_entry = Gtk.Entry()
        self.home_entry.set_hexpand(True)
        add_row(7, "Dossier /home à inclure", self.home_entry)

        self.lang_combo = Gtk.ComboBoxText()
        for code, name in common.LANG_NAMES.items():
            self.lang_combo.append(code, name)
        add_row(8, "Langue de l'interface texte", self.lang_combo)

        outer.pack_start(grid, False, False, 0)

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        save = Gtk.Button(label="Enregistrer la configuration")
        save.get_style_context().add_class("suggested-action")
        save.connect("clicked", lambda *_: self.save_config(True))
        reset = Gtk.Button(label="Recharger")
        reset.connect("clicked", lambda *_: self.load_config())
        buttons.pack_end(save, False, False, 0)
        buttons.pack_end(reset, False, False, 0)
        outer.pack_start(buttons, False, False, 0)

        self.config_status = Gtk.Label(xalign=0)
        outer.pack_start(self.config_status, False, False, 0)
        return outer

    def _on_mode_changed(self, *_args):
        mode = self.mode_combo.get_active_id() or "none"
        self.home_entry.set_sensitive(mode != "none")

    def load_config(self):
        try:
            cfg = common.read_config()
        except Exception as exc:  # noqa: BLE001
            common.show_error(self, "Configuration", f"Impossible de lire la configuration :\n{exc}")
            return
        self.name_entry.set_text(cfg.get("name", ""))
        self.out_entry.set_text(cfg.get("out", ""))
        self.kernel_entry.set_text(cfg.get("kernel", ""))
        self.vmlinuz_entry.set_text(cfg.get("vmlinuz", ""))
        self.arch_label.set_text(cfg.get("arch", ""))
        self.rootdir_entry.set_text(cfg.get("rootdir", ""))
        self.mode_combo.set_active_id(cfg.get("mode", "none"))
        self.home_entry.set_text(cfg.get("home", ""))
        self.lang_combo.set_active_id(cfg.get("lang", "fr"))
        self._on_mode_changed()
        self.config_status.set_markup(
            f"<span foreground='#73ba25'>Configuration chargée — {GLib.markup_escape_text(self.arch_label.get_text())}</span>"
        )
        self._refresh_summary()

    def _collect_config(self) -> dict[str, str]:
        return {
            "name": self.name_entry.get_text().strip(),
            "out": self.out_entry.get_text().strip(),
            "kernel": self.kernel_entry.get_text().strip(),
            "vmlinuz": self.vmlinuz_entry.get_text().strip(),
            "arch": self.arch_label.get_text().strip(),
            "rootdir": self.rootdir_entry.get_text().strip(),
            "mode": self.mode_combo.get_active_id() or "none",
            "home": self.home_entry.get_text().strip(),
            "lang": self.lang_combo.get_active_id() or "fr",
        }

    @staticmethod
    def _valid_outdir(path: str) -> bool:
        if not path.startswith("/") or "/../" in f"/{path}/":
            return False
        exact = {
            "/", "/bin", "/boot", "/dev", "/etc", "/home", "/lib", "/lib64",
            "/opt", "/proc", "/root", "/run", "/sbin", "/srv", "/sys",
            "/tmp", "/usr", "/var", "/mnt", "/media",
        }
        if path in exact:
            return False
        for prefix in ("/bin", "/boot", "/dev", "/etc", "/lib", "/lib64",
                       "/proc", "/run", "/sbin", "/sys", "/usr"):
            if path.startswith(prefix + "/"):
                return False
        return True

    def save_config(self, feedback: bool = False) -> bool:
        cfg = self._collect_config()
        if not cfg["name"]:
            common.show_error(self, "Configuration", "Le nom de l'image est obligatoire.")
            return False
        if "/" in cfg["name"] or "\\" in cfg["name"]:
            common.show_error(self, "Configuration", "Le nom de l'image ne doit pas contenir de / ou de \\.")
            return False
        if not self._valid_outdir(cfg["out"]):
            common.show_error(
                self,
                "Configuration",
                "Dossier de destination invalide.\n\n"
                "Le build efface ce dossier : choisissez un dossier dédié,\n"
                "par exemple /home/votre_nom/ResPinGuy.",
            )
            return False
        rootdirs = cfg["rootdir"].split()
        if not rootdirs or any(
            "/" in item or item in (".", "..") for item in rootdirs
        ):
            common.show_error(
                self,
                "Configuration",
                "La liste des dossiers inclus est invalide.\n\n"
                "Utilisez des noms simples séparés par des espaces :\n"
                "bin boot etc home lib opt root usr var",
            )
            return False
        try:
            common.write_config(cfg)
        except Exception as exc:  # noqa: BLE001
            common.show_error(self, "Configuration", f"Impossible d'enregistrer :\n{exc}")
            return False
        self.config_status.set_markup(
            "<span foreground='#73ba25'>Configuration enregistrée.</span>"
        )
        self._refresh_summary()
        if feedback:
            common.show_info(self, "Configuration", "La configuration a été enregistrée.")
        return True

    # ------------------------------------------------------------------ build

    def _build_build_page(self) -> Gtk.Widget:
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        outer.set_border_width(24)

        self.summary_label = Gtk.Label(xalign=0)
        self.summary_label.set_line_wrap(True)
        outer.pack_start(self.summary_label, False, False, 0)

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.build_button = Gtk.Button(label="Créer l'image ISO")
        self.build_button.get_style_context().add_class("suggested-action")
        self.build_button.connect("clicked", lambda *_: self.start_build())
        buttons.pack_start(self.build_button, False, False, 0)
        outer.pack_start(buttons, False, False, 0)

        self.build_progress = Gtk.ProgressBar()
        self.build_progress.set_show_text(True)
        outer.pack_start(self.build_progress, False, False, 0)
        self.build_step = Gtk.Label(label="Prêt.", xalign=0)
        self.build_step.set_line_wrap(True)
        outer.pack_start(self.build_step, False, False, 0)

        self.build_view = Gtk.TextView()
        self.build_view.set_editable(False)
        self.build_view.set_monospace(True)
        self.build_buffer = self.build_view.get_buffer()
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)
        scrolled.add(self.build_view)
        outer.pack_start(scrolled, True, True, 0)
        return outer

    def _refresh_summary(self):
        cfg = self._collect_config()
        iso = f"{cfg['out']}/{cfg['name']}-{cfg['arch']}.iso"
        mode = {"none": "système seulement", "iso": "/home inclus", "pers": "/home + persistance"}.get(
            cfg.get("mode", "none"), "?"
        )
        self.summary_label.set_markup(
            f"<b>Image :</b> <tt>{GLib.markup_escape_text(iso)}</tt>\n"
            f"<b>Noyau :</b> {GLib.markup_escape_text(cfg.get('kernel') or 'auto')}  "
            f"<b>Architecture :</b> {GLib.markup_escape_text(cfg.get('arch') or '?')}\n"
            f"<b>Contenu :</b> {mode}"
        )

    def start_build(self):
        if self.build_running:
            return
        if not self.save_config(False):
            return
        if not common.elevated_available():
            common.show_error(self, "Build", "sudo ou pkexec est indisponible.")
            return
        if not common.BUILD_SCRIPT.is_file():
            common.show_error(self, "Build", f"Script introuvable : {common.BUILD_SCRIPT}")
            return
        stamp = f"{os.getpid()}-{int(time.time())}"
        self.build_log = Path(f"/tmp/respinguy-build-gui-{stamp}.log")
        self.build_status = Path(f"/tmp/respinguy-build-gui-{stamp}.status")
        for path in (self.build_log, self.build_status):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        try:
            self.build_status.touch()
            self.build_status.chmod(0o644)
        except OSError:
            pass
        cmd = common.elevated_prefix() + [
            "env", f"RPG_STATUS_FILE={self.build_status}",
            "bash", str(common.BUILD_SCRIPT),
        ]
        try:
            fh = open(self.build_log, "wb")
            self.build_fh = fh
            self.build_proc = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=fh,
                stderr=subprocess.STDOUT,
                close_fds=True,
            )
        except OSError as exc:
            common.show_error(self, "Build", f"Impossible de lancer le build :\n{exc}")
            try:
                if self.build_fh:
                    self.build_fh.close()
            except OSError:
                pass
            self.build_fh = None
            return
        self.build_running = True
        self.build_log_text = ""
        self.build_button.set_sensitive(False)
        self.build_progress.set_fraction(0.0)
        self.build_progress.set_text("0 %")
        self.build_step.set_text("Démarrage du build...")
        GLib.timeout_add(300, self._poll_build)

    def _poll_build(self) -> bool:
        if not self.build_running or self.build_proc is None:
            return False
        pct = 0
        msg = "Build en cours..."
        try:
            if self.build_status and self.build_status.exists():
                lines = self.build_status.read_text(encoding="utf-8", errors="replace").splitlines()
                if lines:
                    parts = lines[0].split("|", 1)
                    if parts[0].strip().isdigit():
                        pct = max(0, min(100, int(parts[0].strip())))
                    if len(parts) > 1 and parts[1].strip():
                        msg = parts[1].strip()
        except OSError:
            pass
        self.build_progress.set_fraction(pct / 100.0)
        self.build_progress.set_text(f"{pct} %")
        self.build_step.set_text(msg)
        if self.build_log:
            text = common.tail_text(self.build_log, 200)
            if text != self.build_log_text:
                self.build_log_text = text
                self.build_buffer.set_text(text)
                end = self.build_buffer.get_end_iter()
                self.build_view.scroll_to_iter(end, 0.0, False, 0.0, 1.0)
        if self.build_proc.poll() is None:
            return True
        self.build_running = False
        self.build_button.set_sensitive(True)
        try:
            if self.build_fh:
                self.build_fh.close()
        except OSError:
            pass
        self.build_fh = None
        rc = self.build_proc.returncode
        if rc == 0:
            self.build_step.set_markup("<span foreground='#73ba25'>Build terminé avec succès.</span>")
            cfg = self._collect_config()
            iso = f"{cfg['out']}/{cfg['name']}-{cfg['arch']}.iso"
            common.show_info(self, "Build terminé", f"L'image ISO a été créée :\n\n{iso}")
        else:
            self.build_step.set_markup(f"<span foreground='#ee0000'>Build échoué (code {rc}).</span>")
            common.open_log(self, "Journal du build", self.build_log)
        return False

    # ------------------------------------------------------------------ tools

    def _build_tools_page(self) -> Gtk.Widget:
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        outer.set_border_width(24)
        intro = Gtk.Label(xalign=0)
        intro.set_markup(
            "<span size='large' weight='bold'>Outils</span>\n"
            "Vérifiez les dépendances ou installez-les automatiquement."
        )
        intro.set_line_wrap(True)
        outer.pack_start(intro, False, False, 0)

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        check = Gtk.Button(label="Vérifier les dépendances")
        check.connect("clicked", lambda *_: self.run_tool("Vérification des dépendances",
                                                          [str(common.FILE_DIR / "respinguy-app-dep")]))
        install = Gtk.Button(label="Installer les dépendances")
        install.connect("clicked", lambda *_: self.run_tool(
            "Installation des dépendances",
            [str(common.FILE_DIR / "respinguy-app-dep-force-install")],
        ))
        buttons.pack_start(check, False, False, 0)
        buttons.pack_start(install, False, False, 0)
        outer.pack_start(buttons, False, False, 0)

        self.tools_status = Gtk.Label(xalign=0)
        self.tools_status.set_line_wrap(True)
        outer.pack_start(self.tools_status, False, False, 0)

        self.tools_view = Gtk.TextView()
        self.tools_view.set_editable(False)
        self.tools_view.set_monospace(True)
        self.tools_buffer = self.tools_view.get_buffer()
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)
        scrolled.add(self.tools_view)
        outer.pack_start(scrolled, True, True, 0)
        return outer

    def run_tool(self, title: str, script_args: list[str]):
        if not common.elevated_available():
            common.show_error(self, title, "sudo ou pkexec est indisponible.")
            return
        cmd = common.elevated_prefix() + ["bash"] + script_args
        self.tools_status.set_text(f"{title}...")
        self.tools_buffer.set_text("")

        def done(rc, log_path):
            self.tools_buffer.set_text(common.tail_text(log_path, 2000))
            if rc == 0:
                self.tools_status.set_markup("<span foreground='#73ba25'>Terminé.</span>")
            else:
                self.tools_status.set_markup(f"<span foreground='#ee0000'>Échec (code {rc}).</span>")

        dialog = ProcessDialog(self, title, cmd, on_done=done)
        dialog.run()
        dialog.destroy()

    def _on_delete(self, *_args):
        if self.build_running:
            common.show_info(
                self,
                "Build en cours",
                "La création de l'ISO est en cours.\nAttendez la fin avant de fermer.",
            )
            return True
        return False
