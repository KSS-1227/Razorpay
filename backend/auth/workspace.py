"""
User workspace path resolver.

Every authenticated user has an isolated directory tree:

    data/users/{user_id}/cases/{case_id}/
        uploads/         — raw uploaded documents
        working/         — intermediate pipeline artefacts
        output/          — final knowledge graph + report
        cache/           — LLM response cache
        graph.graphml    — symlink / copy of the final graph (in output/)
        report.json      — generated report (in output/)

No global data/working, data/output, or data/cache folders are used
for user-facing operations.  The global paths in settings.py remain
only as fallbacks for standalone CLI / dev scripts.

Usage
-----
    from backend.auth.workspace import UserWorkspace

    ws = UserWorkspace(user_id="abc123", case_id="def456")
    ws.ensure()                # creates all subdirectories

    builder = MMKGBuilder(
        working_dir=ws.working,
        output_dir=ws.output,
    )
"""
from __future__ import annotations

import shutil
from pathlib import Path

# Base root for all user workspaces
_DATA_ROOT = Path("data/users")


class UserWorkspace:
    """Encapsulates all filesystem paths for one (user_id, case_id) pair."""

    def __init__(self, user_id: str, case_id: str):
        self.user_id  = user_id
        self.case_id  = case_id

        # Root: data/users/{user_id}/cases/{case_id}/
        self.root: Path = _DATA_ROOT / user_id / "cases" / case_id

        # Subdirectories
        self.uploads: Path = self.root / "uploads"
        self.working: Path = self.root / "working"
        self.output:  Path = self.root / "output"
        self.cache:   Path = self.root / "cache"

        # Well-known output files
        self.graph_path:  Path = self.output / "graph.graphml"
        self.report_path: Path = self.output / "report.json"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def ensure(self) -> UserWorkspace:
        """Create all workspace subdirectories if they do not exist.

        Returns self for chaining::

            ws = UserWorkspace(user_id, case_id).ensure()
        """
        for path in (self.uploads, self.working, self.output, self.cache):
            path.mkdir(parents=True, exist_ok=True)
        return self

    def delete(self) -> dict[str, str]:
        """Delete the entire case workspace from the filesystem.

        Continues even if individual directories fail.
        Returns a dict mapping path → result string.
        """
        results: dict[str, str] = {}
        if not self.root.exists():
            return {str(self.root): "not_found"}

        try:
            shutil.rmtree(self.root)
            results[str(self.root)] = "deleted"
        except Exception as exc:
            results[str(self.root)] = f"error: {exc}"

        return results

    def graph_exists(self) -> bool:
        """Return True if the case has a completed knowledge graph."""
        from backend.config import MMKG_NAME
        return self.graph_path.exists() or (self.output / f"{MMKG_NAME}.graphml").exists()

    def __repr__(self) -> str:
        return (
            f"UserWorkspace(user_id={self.user_id!r}, "
            f"case_id={self.case_id!r}, root={self.root!r})"
        )
