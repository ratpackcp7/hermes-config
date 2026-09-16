"""Regression tests for the intentionally non-injecting Hermes orientation diagnostic."""
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SESSION_START = REPO / "scripts" / "session-start.sh"
HANDOFF = REPO / "HANDOFF.md"
CONTRACT = REPO / "STARTUP_CONTRACT.md"


class SessionStartContextTests(unittest.TestCase):
    def test_session_start_is_diagnostic_not_bob_context(self):
        source = SESSION_START.read_text(encoding="utf-8")
        self.assertIn("not injected into model", source)
        self.assertNotIn("bob_startup_bundle", source)
        self.assertNotIn("ACP Rule", source)
        self.assertNotIn("bob-principles", source)
        self.assertNotIn("STARTUP_BUNDLE", source)

    def test_session_start_never_writes_handoff(self):
        source = SESSION_START.read_text(encoding="utf-8")
        self.assertNotIn('open(HANDOFF', source)
        self.assertNotIn("write_text", source)
        self.assertNotIn("write_bytes", source)

    def test_output_has_explicit_context_and_dispatch_pointers(self):
        # project_status.py may be absent in test homes; the diagnostic still
        # prints its non-context contract and exits normally on the live repo.
        proc = subprocess.run(
            [sys.executable, str(SESSION_START), "--dry-run"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Hermes orientation diagnostic", proc.stdout)
        self.assertIn("not automatic model context", proc.stdout)
        self.assertIn("agent-context-contract.md", proc.stdout)
        self.assertIn("agent-dispatch/DISPATCH.md", proc.stdout)
        self.assertNotIn("Bob Startup", proc.stdout)


class HandoffOwnershipCoherenceTests(unittest.TestCase):
    def test_handoff_is_durable_and_not_generated(self):
        content = HANDOFF.read_text(encoding="utf-8")
        self.assertIn("Durable", content)
        self.assertNotIn("Last loaded:", content)
        self.assertIn("agent-context-contract.md", content)
        self.assertNotIn("ACP Rule", content)

    def test_context_contract_retires_hidden_bob_injection(self):
        content = CONTRACT.read_text(encoding="utf-8")
        self.assertIn("must not inject", content)
        self.assertIn("not automatic model context", content)
        self.assertIn("No plugin may silently replace", content)


if __name__ == "__main__":
    unittest.main()
