from __future__ import annotations

import json
from pathlib import Path
import runpy
import subprocess
import unittest
from unittest.mock import Mock, patch

from jinja2 import Environment, StrictUndefined

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "home/.mybin/audio-output"


class AudioOutputTests(unittest.TestCase):
    def setUp(self):
        self.ns = runpy.run_path(SCRIPT)
        self.globals = self.ns["choose_output"].__globals__
        self.sinks = {
            "hdmi": {"name": "hdmi", "description": "Monitor", "active_port": "hdmi-1",
                     "ports": [{"name": "hdmi-1", "description": "HDMI"}]},
            "buds": {"name": "buds", "description": "Nothing Ear (a)"},
        }

    def result(self, value):
        return subprocess.CompletedProcess([], 0, json.dumps(value))

    def test_both_profiles_install_and_bind_the_floating_picker(self):
        installer = runpy.run_path(ROOT / "install.py")
        env = Environment(undefined=StrictUndefined)
        for profile in ("pocket4", "ideapad"):
            with self.subTest(profile=profile):
                self.assertIn(SCRIPT, installer["selected_home_sources"](profile))
                context = {"targets": ["myarch", profile], "home": "/home/tester"}
                binds = env.from_string((ROOT / "src/hyprland/80-keybindings.lua.jinja").read_text()).render(**context)
                rules = env.from_string((ROOT / "src/hyprland/90-window-rules.lua.jinja").read_text()).render(**context)
                self.assertEqual(1, binds.count('bind(mainMod .. " + CTRL + O"'))
                self.assertIn('" --app-id=audio-output-pick "', binds)
                self.assertIn('" -e /home/tester/.mybin/audio-output"', binds)
                self.assertIn("audio-input-pick|audio-output-pick", rules)
        self.assertTrue(SCRIPT.stat().st_mode & 0o100)
        self.assertIn("Super+Ctrl+O\t", (ROOT / "docs/keybindings.tsv").read_text())
        self.assertNotIn("shell=True", SCRIPT.read_text())

    def test_metadata_distinguishes_automatic_from_disconnected_preference(self):
        entries = [{"subject": 0, "key": "default.audio.sink", "value": {"name": "hdmi"}}]
        metadata = {"type": "PipeWire:Interface:Metadata", "props": {"metadata.name": "default"}, "metadata": entries}
        runner = Mock(side_effect=lambda *a, **kw: self.result([metadata]))
        with patch.dict(self.globals, run=runner):
            self.assertEqual(("hdmi", None), self.ns["defaults"]())
            entries.append({"subject": 0, "key": "default.configured.audio.sink", "value": {"name": "offline-buds"}})
            self.assertEqual(("hdmi", "offline-buds"), self.ns["defaults"]())

    def test_missing_metadata_fails_loudly(self):
        with patch.dict(self.globals, run=Mock(return_value=self.result([]))):
            with self.assertRaisesRegex(RuntimeError, "exactly one"):
                self.ns["defaults"]()

    def test_explicit_selection_moves_existing_playback_only(self):
        runner = Mock(return_value=self.result([{"index": 42}, {"index": 43}]))
        with patch.dict(self.globals, run=runner, sinks_by_name=lambda: self.sinks,
                        defaults=lambda: ("buds", "buds")):
            self.assertEqual("buds", self.ns["apply_selection"]("buds"))
        self.assertEqual([
            ["pactl", "set-default-sink", "buds"],
            ["pactl", "--format=json", "list", "sink-inputs"],
            ["pactl", "move-sink-input", "42", "buds"],
            ["pactl", "move-sink-input", "43", "buds"],
        ], [call.args[0] for call in runner.call_args_list])

    def test_automatic_clears_output_not_microphone_or_camera(self):
        runner = Mock(return_value=self.result([{"index": 42}]))
        with patch.dict(self.globals, run=runner, defaults=lambda: ("hdmi", None)):
            self.assertEqual("hdmi", self.ns["apply_selection"](None))
        self.assertEqual([
            ["wpctl", "clear-default", "0"],
            ["pactl", "--format=json", "list", "sink-inputs"],
            ["pactl", "move-sink-input", "42", "hdmi"],
        ], [call.args[0] for call in runner.call_args_list])

    def test_device_disconnected_during_picker_is_not_pinned(self):
        runner = Mock()
        with patch.dict(self.globals, run=runner, sinks_by_name=lambda: {}):
            with self.assertRaisesRegex(RuntimeError, "disconnected"):
                self.ns["apply_selection"]("buds")
        runner.assert_not_called()

    def test_selection_waits_for_async_metadata(self):
        runner = Mock(return_value=self.result([]))
        states = Mock(side_effect=[("hdmi", None), ("hdmi", "buds"), ("buds", "buds")])
        with patch.dict(self.globals, run=runner, defaults=states, sinks_by_name=lambda: self.sinks), patch("time.sleep") as sleep:
            self.assertEqual("buds", self.ns["apply_selection"]("buds"))
            self.assertEqual(2, sleep.call_count)

    def test_selection_that_never_takes_effect_fails_loudly(self):
        runner = Mock()
        with patch.dict(self.globals, run=runner, defaults=lambda: ("hdmi", None), sinks_by_name=lambda: self.sinks), patch("time.monotonic", side_effect=[0, 3]):
            with self.assertRaisesRegex(RuntimeError, "did not apply"):
                self.ns["apply_selection"]("buds")
        self.assertEqual(1, runner.call_count)

    def picker(self, token=None, *, preferred=None, returncode=0, invalid=False):
        rows_seen = []
        header_seen = []
        def runner(argv, **kwargs):
            if argv[0] == "fzf":
                rows = kwargs["stdin"].splitlines()
                rows_seen.extend(rows)
                header_seen.append(argv[argv.index("--header") + 1])
                result = "invalid row" if invalid else next(row for row in rows if row.endswith("\t" + (token or "auto")))
                return subprocess.CompletedProcess(argv, returncode, result + "\n")
            return subprocess.CompletedProcess(argv, 0, "")
        apply = Mock(side_effect=lambda selected: "hdmi" if selected is None else selected)
        with patch.dict(self.globals, run=runner, defaults=lambda: ("hdmi", preferred),
                        sinks_by_name=lambda: self.sinks, apply_selection=apply):
            self.ns["choose_output"]()
        return apply, rows_seen, header_seen

    def test_picker_maps_device_token_to_sink_name(self):
        apply, rows, headers = self.picker("1")
        apply.assert_called_once_with("buds")
        self.assertIn("Automatic", rows[0])
        self.assertIn("● HDMI", rows[1])
        self.assertIn("Nothing Ear (a)", rows[2])
        self.assertTrue(headers[0].startswith("Automatic\n"))

    def test_picker_can_clear_a_disconnected_preference(self):
        apply, _, headers = self.picker("auto", preferred="offline-buds")
        apply.assert_called_once_with(None)
        self.assertIn("Preferred output disconnected: offline-buds", headers[0])

    def test_cancel_changes_nothing(self):
        for code in (1, 130):
            apply, _, _ = self.picker(returncode=code)
            apply.assert_not_called()

    def test_picker_failure_and_unknown_selection_are_loud(self):
        with self.assertRaisesRegex(RuntimeError, "status 2"):
            self.picker(returncode=2)
        with self.assertRaisesRegex(RuntimeError, "unknown output"):
            self.picker(invalid=True)


if __name__ == "__main__":
    unittest.main()
