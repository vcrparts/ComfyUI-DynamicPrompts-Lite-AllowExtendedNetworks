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


def _format_wildcard_name(rel_posix_path: str) -> str:
    """Convert 'folder/colors.txt' into '__folder/colors__'."""
    stem_path = Path(rel_posix_path).with_suffix("").as_posix()
    return f"__{stem_path}__"


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
                old_map = (
                    {path: (mtime, size) for path, mtime, size in self._manifest}
                    if self._manifest is not None
                    else {}
                )
                new_map = {path: (mtime, size) for path, mtime, size in manifest}

                added = [p for p in new_map if p not in old_map]
                modified = [
                    p for p in new_map if p in old_map and new_map[p] != old_map[p]
                ]
                removed = [p for p in old_map if p not in new_map]

                self._manifest = manifest
                self._revision += 1

                print(f"[DynamicPrompts-Lite] Wildcards refreshed (rev {self._revision}):")
                for p in added:
                    print(f"  + Added:    {_format_wildcard_name(p)}")
                for p in modified:
                    print(f"  ~ Modified: {_format_wildcard_name(p)}")
                for p in removed:
                    print(f"  - Removed:  {_format_wildcard_name(p)}")
            else:
                print("[DynamicPrompts-Lite] Wildcard refresh clicked: no file changes detected.")

            return RefreshResult(
                changed=changed,
                revision=self._revision,
                file_count=len(manifest),
            )


wildcard_refresh_state = WildcardRefreshState()
