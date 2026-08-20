"""Shared command-line presentation helpers."""

from __future__ import annotations

import argparse
from importlib.metadata import PackageNotFoundError, version


class DefaultsHelpFormatter(argparse.ArgumentDefaultsHelpFormatter):
    """Show meaningful defaults without displaying ``None`` placeholders."""

    def _get_help_string(self, action: argparse.Action) -> str:
        help_text = action.help or ""
        if action.default is None or action.default is argparse.SUPPRESS:
            return help_text
        return super()._get_help_string(action)


def package_version() -> str:
    """Return the installed distribution version or a source-tree fallback."""

    try:
        return version("ionosphere-fdtd")
    except PackageNotFoundError:
        return "unknown"


def add_version_argument(parser: argparse.ArgumentParser) -> None:
    """Add the common version-reporting option."""

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {package_version()}",
    )
