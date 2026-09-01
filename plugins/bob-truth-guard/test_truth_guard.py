import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE = Path(__file__).with_name("__init__.py")
SPEC = importlib.util.spec_from_file_location("bob_truth_guard", MODULE)
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)


class TruthGuardTests(unittest.TestCase):
    def setUp(self):
        guard._turns.clear()

    def test_unsupported_operational_claim_fails_closed(self):
        guard._pre_llm_call("s1", "What is the current gateway status?")
        result = guard._transform_llm_output("I checked the gateway and it is healthy.", "s1")
        self.assertIn("I don't know", result)
        self.assertIn("did not inspect", result)

    def test_unsupported_status_assertion_fails_closed_without_inspection_words(self):
        guard._pre_llm_call("s1b", "What is the current gateway status?")
        result = guard._transform_llm_output("The gateway is healthy.", "s1b")
        self.assertIn("I don't know", result)

    def test_tool_evidence_is_disclosed(self):
        guard._pre_llm_call("s2", "What is the current gateway status?")
        guard._post_tool_call(session_id="s2", tool_name="terminal", result='{"output":"ok"}')
        result = guard._transform_llm_output("The gateway is healthy.", "s2")
        self.assertTrue(result.endswith("Evidence this turn: terminal."))

    def test_startup_inventory_is_deterministic(self):
        guard._pre_llm_call("s3", "What files are loaded at startup?")
        result = guard._transform_llm_output("I read several files.", "s3")
        self.assertIn("Startup inventory — verified from local files", result)
        self.assertNotIn("I read several files.", result)

    def test_safe_file_is_materialized_and_linked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "README.md"
            source.write_text("visible context\n", encoding="utf-8")
            links = root / "served"
            url = guard._materialize_link(
                source, link_root=links, allowed_root=root, url_base="http://tailnet:8889"
            )
            self.assertEqual(url, "http://tailnet:8889/README.md".replace("README.md", f"{next(links.iterdir()).name}"))
            self.assertEqual(next(links.iterdir()).read_text(encoding="utf-8"), "visible context\n")

    def test_sensitive_file_is_never_materialized(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / ".env"
            source.write_text("TOKEN=do-not-publish\n", encoding="utf-8")
            self.assertIsNone(guard._materialize_link(source, link_root=root / "served", allowed_root=root))

    def test_known_name_becomes_markdown_link(self):
        response = guard._linkify_paths("Read AGENTS.md first.")
        self.assertIn("[", response)
        self.assertIn("100.101.249.113:8889/bob-links/", response)

    def test_file_links_do_not_require_turn_state(self):
        result = guard._transform_llm_output("Read /home/chris/AGENTS.md.", "unknown-session")
        self.assertIn("100.101.249.113:8889/bob-links/", result)


if __name__ == "__main__":
    unittest.main()
