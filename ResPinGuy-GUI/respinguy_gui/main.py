#!/usr/bin/env python3
"""Point d'entrée de l'interface graphique ResPinGuy."""

from __future__ import annotations

import argparse
import sys

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

from . import common  # noqa: E402


class ResPinGuyApp(Gtk.Application):
    def __init__(self, install_mode: bool = False):
        super().__init__(application_id=common.APP_ID)
        self.install_mode = install_mode
        self.window = None

    def do_activate(self):  # noqa: N802
        if self.window is not None:
            self.window.present()
            return
        common.apply_theme()
        live = common.is_live()
        if self.install_mode or live:
            if not live:
                common.show_error(
                    None,
                    "Installation impossible",
                    "L'installateur ResPinGuy fonctionne uniquement depuis le live.\n\n"
                    "Depuis le live, lancez simplement : install",
                )
                self.quit()
                return
            from .installer import InstallerWindow
            self.window = InstallerWindow(self)
        else:
            from .main_window import MainWindow
            self.window = MainWindow(self)
        self.window.connect("destroy", self._on_destroy)
        self.window.show_all()

    def _on_destroy(self, *_args):
        self.window = None
        self.quit()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="respinguy-g",
        description="Interface graphique ResPinGuy.",
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="ouvrir directement l'installateur (live uniquement)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"ResPinGuy {common.read_version()}",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    app = ResPinGuyApp(install_mode=args.install)
    return app.run([sys.argv[0]])


if __name__ == "__main__":
    raise SystemExit(main())
