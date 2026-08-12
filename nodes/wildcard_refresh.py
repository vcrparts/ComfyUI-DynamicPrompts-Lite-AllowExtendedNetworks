from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from threading import Lock

SUPPORTED_WILDCARD_SUFFIXES = frozenset({".txt", ".json", ".yaml"})


@dataclass(frozen=True)
class RefreshResult:
    changed: bool
    revision: int
    file_count: int


def get_wildcards_folder() -> Path:
    """Return the wildcard directory owned by this plugin."""
    # Honor a "wildcards" entry registered via extra_model_paths.yaml, if present.
    try:
        import folder_paths

        registered = folder_paths.get_folder_paths("wildcards")
        if registered:
            path = Path(registered[0])
            if path.exists():
                return path
    except (KeyError, Exception):
        pass

    plugin_wildcards = Path(__file__).resolve().parent.parent / "wildcards"
    if plugin_wildcards.exists():
        return plugin_wildcards

    from folder_paths import base_path

    wildcard_path = Path(base_path) / "wildcards"
    if wildcard_path.exists():
        return wildcard_path

    plugin_wildcards.mkdir(parents=True, exist_ok=True)
    return plugin_wildcards


def _build_manifest(root: Path) -> tuple[tuple[str, int, int], ...]:
    """Build a lightweight fingerprint for files Dynamic Prompts can read."""
    entries: list[tuple[str, int, int]] = []
    for directory, directories, filenames in os.walk(root, followlinks=True):
        directories[:] = [name for name in directories if not name.startswith(".")]
        for filename in filenames:
            path = Path(directory) / filename
            if path.suffix not in SUPPORTED_WILDCARD_SUFFIXES:
                continue
            stat = path.stat()
            entries.append(
                (
                    path.relative_to(root).as_posix(),
                    stat.st_mtime_ns,
                    stat.st_size,
                ),
            )
    return tuple(sorted(entries))


class WildcardRefreshState:
    """Tracks wildcard file changes without reading their full text on every click."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._manifest: tuple[tuple[str, int, int], ...] | None = None
        self._revision = 0

    @property
    def revision(self) -> int:
        with self._lock:
            return self._revision

    def refresh(self) -> RefreshResult:
        manifest = _build_manifest(get_wildcards_folder())
        with self._lock:
            changed = manifest != self._manifest
            if changed:
                self._manifest = manifest
                self._revision += 1
            return RefreshResult(
                changed=changed,
                revision=self._revision,
                file_count=len(manifest),
            )


wildcard_refresh_state = WildcardRefreshState()
