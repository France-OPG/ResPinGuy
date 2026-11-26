#!/usr/bin/env python3
"""Installateur graphique ResPinGuy (GTK3)."""

from __future__ import annotations

import os
import pwd
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GObject, GLib, Gtk  # noqa: E402

from . import common  # noqa: E402


class InstallerWindow(Gtk.Assistant):
    def __init__(self, app=None):
        super().__init__(application=app) if app else super().__init__()
        self.set_title(f"Installateur ResPinGuy {common.read_version()}")
        self.set_default_size(900, 650)
        self.set_icon_name("respinguy")
        self.set_modal(False)

        self.disks: list[dict] = []
        self.live_disk = ""
        self.proc: subprocess.Popen | None = None
        self.running = False
        self.log_path: Path | None = None
        self.status_path: Path | None = None
        self.tmpdir: Path | None = None
        self.log_text = ""
        self.log_fh = None

        self._build_pages()
        self.connect("prepare", self._on_prepare)
        self.connect("apply", self._on_apply)
        self.connect("cancel", self._on_cancel)
        self.connect("close", self._on_close)
        self.connect("delete-event", self._on_delete)

        self.refresh_disks()
        self.show_all()
        self._update_summary_buttons()

    # ------------------------------------------------------------------ pages

    def _page(self, widget, title, ptype):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        page.set_border_width(24)
        page.pack_start(widget, True, True, 0)
        self.append_page(page)
        self.set_page_title(page, title)
        self.set_page_type(page, ptype)
        return page

    def _label(self, markup: str, wrap: bool = True) -> Gtk.Label:
        label = Gtk.Label()
        label.set_markup(markup)
        label.set_xalign(0)
        label.set_line_wrap(wrap)
        return label

    def _build_pages(self):
        # 1. Bienvenue
        intro = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        intro.pack_start(self._label(
            f"<span size='xx-large' weight='bold'>ResPinGuy {common.read_version()}</span>"
            "\n<span size='large'>Installer le système sur le disque</span>"
        ), False, False, 0)
        intro.pack_start(self._label(
            "Cet assistant installe le système du live sur un disque.\n\n"
            "<b>Attention :</b> le disque choisi sera entièrement effacé.\n"
            "Toutes ses données seront perdues.\n\n"
            "Le système installé est une copie de la distribution du live."
        ), False, False, 0)
        intro.pack_start(self._label(
            "<span foreground='#73ba25'>Conseil :</span> sauvegardez vos données avant de continuer."
        ), False, False, 0)
        self.intro_page = self._page(intro, "Bienvenue", Gtk.AssistantPageType.INTRO)
        self.set_page_complete(self.intro_page, True)

        # 2. Disque
        disk_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        disk_box.pack_start(self._label(
            "<b>Choisissez le disque cible.</b>\n"
            "Le disque du live est automatiquement exclu."
        ), False, False, 0)
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.disk_combo = Gtk.ComboBoxText()
        self.disk_combo.set_hexpand(True)
        self.disk_combo.connect("changed", self._on_disk_changed)
        refresh = Gtk.Button(label="Rafraîchir")
        refresh.connect("clicked", lambda *_: self.refresh_disks())
        row.pack_start(self.disk_combo, True, True, 0)
        row.pack_start(refresh, False, False, 0)
        disk_box.pack_start(row, False, False, 0)
        self.disk_details = self._label("")
        disk_box.pack_start(self.disk_details, False, False, 0)
        self.disk_page = self._page(disk_box, "Disque", Gtk.AssistantPageType.CONTENT)
        self.set_page_complete(self.disk_page, False)

        # 3. Options
        opts = Gtk.Grid(column_spacing=12, row_spacing=10)
        opts.set_hexpand(True)
        opts.attach(self._label("<b>Nom de la machine</b>"), 0, 0, 2, 1)
        self.host_entry = Gtk.Entry()
        self.host_entry.set_hexpand(True)
        opts.attach(self.host_entry, 0, 1, 2, 1)

        opts.attach(self._label("<b>Mot de passe root</b> (optionnel)"), 0, 2, 2, 1)
        self.root_pw = self._password_entry()
        self.root_pw2 = self._password_entry()
        opts.attach(self.root_pw, 0, 3, 1, 1)
        opts.attach(self.root_pw2, 1, 3, 1, 1)

        opts.attach(self._label("<b>Mot de passe utilisateur</b> (optionnel)"), 0, 4, 2, 1)
        self.user_combo = Gtk.ComboBoxText()
        self.user_combo.append("none", "(aucun)")
        for entry in pwd.getpwall():
            if 1000 <= entry.pw_uid < 65534:
                self.user_combo.append(entry.pw_name, entry.pw_name)
        self.user_combo.set_active_id("none")
        self.user_combo.connect("changed", self._on_user_changed)
        opts.attach(self.user_combo, 0, 5, 2, 1)
        self.user_pw = self._password_entry()
        self.user_pw2 = self._password_entry()
        opts.attach(self.user_pw, 0, 6, 1, 1)
        opts.attach(self.user_pw2, 1, 6, 1, 1)

        for entry in (self.root_pw, self.root_pw2, self.user_pw, self.user_pw2):
            entry.connect("changed", self._update_options_complete)
        opts.attach(self._label(
            "<span size='small'>Laissez vide pour conserver les mots de passe du système source.</span>"
        ), 0, 7, 2, 1)

        self.options_page = self._page(opts, "Options", Gtk.AssistantPageType.CONTENT)
        self.set_page_complete(self.options_page, True)
        self._on_user_changed()

        # 4. Confirmation
        confirm = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.confirm_label = self._label("")
        confirm.pack_start(self.confirm_label, False, False, 0)
        confirm.pack_start(self._label(
            "<b>Confirmation obligatoire.</b>\n"
            "Tapez le chemin du disque, puis le mot EFFACER."
        ), False, False, 0)
        grid = Gtk.Grid(column_spacing=12, row_spacing=8)
        grid.attach(Gtk.Label(label="Chemin du disque :", xalign=0), 0, 0, 1, 1)
        self.confirm_disk = Gtk.Entry()
        self.confirm_disk.set_hexpand(True)
        grid.attach(self.confirm_disk, 1, 0, 1, 1)
        grid.attach(Gtk.Label(label="Mot de confirmation :", xalign=0), 0, 1, 1, 1)
        self.confirm_word = Gtk.Entry()
        self.confirm_word.set_hexpand(True)
        grid.attach(self.confirm_word, 1, 1, 1, 1)
        confirm.pack_start(grid, False, False, 0)
        self.confirm_disk.connect("changed", self._update_confirm_complete)
        self.confirm_word.connect("changed", self._update_confirm_complete)
        self.confirm_page = self._page(confirm, "Confirmation", Gtk.AssistantPageType.CONFIRM)
        self.set_page_complete(self.confirm_page, False)

        # 5. Progression
        progress = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)
        progress.pack_start(self.progress_bar, False, False, 0)
        self.progress_label = self._label("Préparation...")
        progress.pack_start(self.progress_label, False, False, 0)
        self.log_view = Gtk.TextView()
        self.log_view.set_editable(False)
        self.log_view.set_monospace(True)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)
        scrolled.add(self.log_view)
        progress.pack_start(scrolled, True, True, 0)
        self.progress_page = self._page(progress, "Installation", Gtk.AssistantPageType.PROGRESS)
        self.set_page_complete(self.progress_page, False)

        # 6. Résumé
        summary = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.summary_label = self._label("")
        summary.pack_start(self.summary_label, False, False, 0)
        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.log_button = Gtk.Button(label="Voir le journal")
        self.log_button.connect("clicked", self._on_show_log)
        self.reboot_button = Gtk.Button(label="Redémarrer")
        self.reboot_button.get_style_context().add_class("destructive-action")
        self.reboot_button.connect("clicked", self._on_reboot)
        buttons.pack_end(self.reboot_button, False, False, 0)
        buttons.pack_end(self.log_button, False, False, 0)
        summary.pack_start(buttons, False, False, 0)
        self.summary_page = self._page(summary, "Terminé", Gtk.AssistantPageType.SUMMARY)

    def _password_entry(self) -> Gtk.Entry:
        entry = Gtk.Entry()
        entry.set_visibility(False)
        entry.set_input_purpose(Gtk.InputPurpose.PASSWORD)
        entry.set_placeholder_text("mot de passe")
        entry.set_hexpand(True)
        return entry

    # ------------------------------------------------------------------ events

    def refresh_disks(self):
        self.disk_combo.remove_all()
        self.disks = []
        try:
            disks, live = common.list_disks()
        except Exception as exc:  # noqa: BLE001
            common.show_error(self, "Disques", f"Impossible de lister les disques :\n{exc}")
            self.disk_details.set_markup("<span foreground='#ee0000'>Aucun disque détecté.</span>")
            self.set_page_complete(self.disk_page, False)
            return
        self.live_disk = live
        self.disks = disks
        for disk in disks:
            label = f"{disk['name']}  {disk['size']}  {disk['model']}".strip()
            self.disk_combo.append(disk["name"], label)
        if disks:
            self.disk_combo.set_active(0)
            self.disk_details.set_markup(
                f"<span foreground='#73ba25'>{len(disks)} disque(s) disponible(s).</span>"
                + (f"\nLive exclu : <tt>{live}</tt>" if live else "")
            )
        else:
            self.disk_details.set_markup(
                "<span foreground='#ee0000'>Aucun disque disponible.</span>\n"
                "Le disque du live est exclu."
            )
        self._on_disk_changed()

    def _selected_disk(self) -> str:
        return self.disk_combo.get_active_id() or ""

    def _on_disk_changed(self, *_args):
        disk = self._selected_disk()
        self.set_page_complete(self.disk_page, bool(disk))
        if disk:
            for d in self.disks:
                if d["name"] == disk:
                    self.disk_details.set_markup(
                        f"<b>{d['name']}</b>  {d['size']}  {d['model']}"
                    )
                    break
        self._update_confirm_complete()

    def _on_user_changed(self, *_args):
        active = self.user_combo.get_active_id() not in (None, "", "none")
        self.user_pw.set_sensitive(active)
        self.user_pw2.set_sensitive(active)
        self._update_options_complete()

    def _update_options_complete(self, *_args):
        ok = self.root_pw.get_text() == self.root_pw2.get_text()
        if self.user_combo.get_active_id() not in (None, "", "none"):
            ok = ok and self.user_pw.get_text() == self.user_pw2.get_text()
        self.set_page_complete(self.options_page, ok)

    def _update_confirm_complete(self, *_args):
        disk = self._selected_disk()
        ok = bool(disk) and self.confirm_disk.get_text().strip() == disk \
            and self.confirm_word.get_text().strip() == "EFFACER"
        self.set_page_complete(self.confirm_page, ok)
        if disk:
            self.confirm_label.set_markup(
                f"<b>Disque cible :</b> <tt>{disk}</tt>\n"
                f"<b>Machine :</b> {GLib.markup_escape_text(self.host_entry.get_text().strip() or 'valeur par défaut')}\n"
                "<span foreground='#ee0000'><b>Toutes les données de ce disque seront effacées.</b></span>"
            )

    def _on_prepare(self, _assistant, page):
        if page is self.options_page and not self.host_entry.get_text().strip():
            try:
                with open("/etc/hostname", encoding="utf-8", errors="ignore") as fh:
                    default = fh.read().strip()
            except OSError:
                default = ""
            self.host_entry.set_text(default or "respinguy")
        if page is self.confirm_page:
            self._update_confirm_complete()

    def _on_apply(self, _assistant):
        if self.running:
            return
        disk = self._selected_disk()
        if not disk:
            common.show_error(self, "Disque", "Aucun disque sélectionné.")
            return
        if self.confirm_disk.get_text().strip() != disk or self.confirm_word.get_text().strip() != "EFFACER":
            common.show_error(self, "Confirmation", "La confirmation du disque est incorrecte.")
            return
        if not Path(disk).exists():
            common.show_error(self, "Disque", f"Le disque {disk} n'existe plus.")
            return
        if self.root_pw.get_text() != self.root_pw2.get_text():
            common.show_error(self, "Mot de passe", "Les mots de passe root ne correspondent pas.")
            return
        if self.user_combo.get_active_id() not in (None, "", "none") and self.user_pw.get_text() != self.user_pw2.get_text():
            common.show_error(self, "Mot de passe", "Les mots de passe utilisateur ne correspondent pas.")
            return
        if not common.elevated_available():
            common.show_error(
                self,
                "Élévation indisponible",
                "Impossible d'utiliser sudo ou pkexec.\n\n"
                "Dans le live ResPinGuy, lancez l'installateur depuis une session normale.\n"
                "Sinon, utilisez l'installateur texte :\n"
                "sudo respinguy-install",
            )
            return
        self.start_install(disk)

    def start_install(self, disk: str):
        if self.proc is not None or self.running:
            return
        try:
            self.tmpdir = Path(tempfile.mkdtemp(prefix="respinguy-gui-"))
            self.tmpdir.chmod(0o700)
        except OSError as exc:
            common.show_error(self, "Erreur", f"Impossible de créer le dossier temporaire :\n{exc}")
            return

        root_file = self.tmpdir / "root.pw"
        user_file = self.tmpdir / "user.pw"
        user_name = self.user_combo.get_active_id() or ""
        if user_name == "none":
            user_name = ""
        if self.root_pw.get_text():
            root_file.write_text(f"root:{self.root_pw.get_text()}\n", encoding="utf-8")
            root_file.chmod(0o600)
        if user_name and self.user_pw.get_text():
            user_file.write_text(f"{user_name}:{self.user_pw.get_text()}\n", encoding="utf-8")
            user_file.chmod(0o600)

        stamp = f"{os.getpid()}-{int(time.time())}"
        self.log_path = Path(f"/tmp/respinguy-install-gui-{stamp}.log")
        self.status_path = Path(f"/tmp/respinguy-install-gui-{stamp}.status")
        for path in (self.log_path, self.status_path):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass

        env = {
            "RPG_WORKER": "1",
            "RPG_DISK": disk,
            "RPG_HOST": self.host_entry.get_text().strip() or "respinguy",
            "RPG_ROOTPW_FILE": str(root_file) if root_file.exists() else "",
            "RPG_USERPW_FILE": str(user_file) if user_file.exists() else "",
            "RPG_USER_NAME": user_name,
            "RPG_LOG": str(self.log_path),
            "RPG_STATUS": str(self.status_path),
        }
        cmd = common.elevated_prefix() + ["env"] + [f"{k}={v}" for k, v in env.items()] + [
            "bash", str(common.INSTALLER)
        ]
        try:
            log_fh = open(self.log_path, "wb")
            self.log_fh = log_fh
            self.proc = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=log_fh,
                stderr=subprocess.STDOUT,
                close_fds=True,
            )
        except OSError as exc:
            common.show_error(self, "Erreur", f"Impossible de lancer l'installateur :\n{exc}")
            try:
                if self.log_fh:
                    self.log_fh.close()
            except OSError:
                pass
            self.log_fh = None
            self._cleanup_tmp()
            return

        self.running = True
        self.log_text = ""
        self.set_deletable(False)
        self.progress_bar.set_fraction(0.0)
        self.progress_bar.set_text("0 %")
        self.progress_label.set_text("Démarrage de l'installation...")
        self.set_page_complete(self.progress_page, False)
        self.set_current_page(self.get_n_pages() - 2)  # page progression
        GLib.timeout_add(300, self._poll)

    def _poll(self) -> bool:
        if not self.running or self.proc is None:
            return False
        pct = 0
        msg = "Installation en cours..."
        try:
            if self.status_path and self.status_path.exists():
                line = self.status_path.read_text(encoding="utf-8", errors="replace").splitlines()
                if line:
                    parts = line[0].split("|", 1)
                    if parts[0].strip().isdigit():
                        pct = max(0, min(100, int(parts[0].strip())))
                    if len(parts) > 1 and parts[1].strip():
                        msg = parts[1].strip()
        except OSError:
            pass
        self.progress_bar.set_fraction(pct / 100.0)
        self.progress_bar.set_text(f"{pct} %")
        self.progress_label.set_text(msg)
        if self.log_path:
            text = common.tail_text(self.log_path, 120)
            if text != self.log_text:
                self.log_text = text
                buf = self.log_view.get_buffer()
                buf.set_text(text)
                end = buf.get_end_iter()
                self.log_view.scroll_to_iter(end, 0.0, False, 0.0, 1.0)
        if self.proc.poll() is None:
            return True
        self.running = False
        self._finish()
        return False

    def _finish(self):
        rc = self.proc.returncode if self.proc else 1
        try:
            if self.log_fh:
                self.log_fh.close()
        except OSError:
            pass
        self.log_fh = None
        self.set_deletable(True)
        self._cleanup_tmp()
        if rc == 0:
            self.summary_label.set_markup(
                "<span size='x-large' foreground='#73ba25'><b>Installation terminée</b></span>\n\n"
                f"Le système a été installé sur <tt>{self._selected_disk()}</tt>.\n"
                "Vous pouvez redémarrer sur le disque installé.\n\n"
                f"Journal : <tt>{self.log_path}</tt>"
            )
            self.reboot_button.show()
        else:
            self.summary_label.set_markup(
                "<span size='x-large' foreground='#ee0000'><b>Installation échouée</b></span>\n\n"
                f"L'installateur s'est arrêté avec le code <b>{rc}</b>.\n"
                "Consultez le journal pour identifier la cause.\n\n"
                f"Journal : <tt>{self.log_path}</tt>"
            )
            self.reboot_button.hide()
            self.log_button.show()
        self.set_current_page(self.get_n_pages() - 1)
        self.set_page_complete(self.summary_page, True)
        self._update_summary_buttons()

    def _update_summary_buttons(self):
        self.log_button.set_visible(True)
        self.reboot_button.set_visible(True)

    def _cleanup_tmp(self):
        if self.tmpdir:
            shutil.rmtree(self.tmpdir, ignore_errors=True)
            self.tmpdir = None

    def _on_show_log(self, *_args):
        if self.log_path:
            common.open_log(self, "Journal d'installation", self.log_path)

    def _on_reboot(self, *_args):
        prefix = common.elevated_prefix()
        if not prefix:
            common.show_error(self, "Redémarrage", "sudo/pkexec est introuvable.")
            return
        subprocess.Popen(prefix + ["reboot"])

    def _on_cancel(self, _assistant):
        if self.running:
            common.show_info(
                self,
                "Installation en cours",
                "L'installation est en cours.\nAttendez la fin avant de fermer.",
            )
            try:
                self.stop_emission_by_name("cancel")
            except Exception:  # noqa: BLE001
                pass

    def _on_close(self, _assistant):
        if self.running:
            try:
                self.stop_emission_by_name("close")
            except Exception:  # noqa: BLE001
                pass
            return
        self.destroy()

    def _on_delete(self, *_args):
        if self.running:
            common.show_info(
                self,
                "Installation en cours",
                "L'installation est en cours.\nAttendez la fin avant de fermer.",
            )
            return True
        self._cleanup_tmp()
        return False
