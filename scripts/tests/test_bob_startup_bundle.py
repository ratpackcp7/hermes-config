import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))
import bob_startup_bundle as bundle


class StartupBundleTests(unittest.TestCase):
    def test_completed_scratchpad_is_not_active(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "scratchpad.md"
            path.write_text("# Scratchpad\n\n## Completed: prior work\n\n- merged\n", encoding="utf-8")
            parsed = bundle.parse_scratchpad(path=path)
            self.assertFalse(parsed["active"])
            self.assertEqual(parsed["summary"], "none")

    def test_startup_brief_is_bounded_and_blocker_first(self):
        payload = {
            "staged_restarts": {"pending_count": 0, "pending_items": []},
            "scratchpad": {"active": False, "summary": "none"},
            "project_summary": {
                "available": True,
                "counts": {"active": 8, "blocked": 0, "stale": 21},
                "highlights": [
                    {"name": f"project-{n}", "next_step": "do the next thing"}
                    for n in range(6)
                ],
            },
            "acerserver_excerpt": "x" * 5000,
        }
        text = bundle.build_injection_text(payload)
        self.assertLessEqual(len(text), bundle.MAX_INJECTION_CHARS)
        self.assertIn("Restart queue: clear.", text)
        self.assertIn("Active projects: 8 | blocked: 0", text)
        self.assertNotIn("stale: 21", text)
        self.assertNotIn("Mandatory acknowledgment", text)
        self.assertIn("agent-bootstrap", text)
        self.assertIn("ACP Rule 00-90", text)
        self.assertIn("Bob ops preferences: ~/.hermes/bob-principles.md", text)
        self.assertNotIn("ACP Rule 00-80", text)
        self.assertNotIn("~/bob-principles.md", text)
        self.assertEqual(bundle.BOB_PRINCIPLES_PATH, REPO / "bob-principles.md")


if __name__ == "__main__":
    unittest.main()
