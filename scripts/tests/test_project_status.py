import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parents[1]))
from project_status import build_status, markdown_view


class ProjectStatusTests(unittest.TestCase):
    def test_uses_only_canonical_roots_and_classifies_handoffs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            active = root / "active"
            retired = root / "retired"
            active.mkdir()
            retired.mkdir()
            (active / "HANDOFF.md").write_text("# Handoff\n\n## In Flight\n- Build scanner\n\n## Next Steps\n1. Add tests\n")
            (retired / "HANDOFF.md").write_text("# Handoff\n\n## Status: RETIRED\n")
            index = root / "AGENT_INDEX.md"
            index.write_text(
                "## Project Roots\n\n| Name | Path | Markers | Wiki |\n|---|---|---|---|\n"
                f"| active | {active} | HANDOFF.md | - |\n| retired | {retired} | HANDOFF.md | - |\n"
            )
            status = build_status(index, now=datetime.now(timezone.utc))
            self.assertEqual(status["counts"]["active"], 1)
            self.assertEqual(status["counts"]["retired"], 1)
            self.assertIn("Add tests", markdown_view(status))

    def test_old_in_flight_handoff_is_stale_not_active(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "old"
            project.mkdir()
            handoff = project / "HANDOFF.md"
            handoff.write_text("# Handoff\n\n## In Flight\n- Old work\n")
            old = (datetime.now(timezone.utc) - timedelta(days=30)).timestamp()
            os.utime(handoff, (old, old))
            index = root / "AGENT_INDEX.md"
            index.write_text(
                "## Project Roots\n\n| Name | Path | Markers | Wiki |\n|---|---|---|---|\n"
                f"| old | {project} | HANDOFF.md | - |\n"
            )
            status = build_status(index, now=datetime.now(timezone.utc))
            self.assertEqual(status["counts"]["stale"], 1)
            self.assertEqual(status["counts"]["active"], 0)


if __name__ == "__main__":
    unittest.main()
