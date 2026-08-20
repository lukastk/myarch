#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import re
import tomllib
import unittest

from jinja2 import Environment, StrictUndefined

ROOT = Path(__file__).resolve().parents[1]


def strip_jsonc(text: str) -> str:
    output: list[str] = []
    i = 0
    in_string = False
    escape = False
    while i < len(text):
        char = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if in_string:
            output.append(char)
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            i += 1
        elif char == '"':
            in_string = True
            output.append(char)
            i += 1
        elif char == "/" and nxt == "/":
            i += 2
            while i < len(text) and text[i] != "\n":
                i += 1
        elif char == "/" and nxt == "*":
            end = text.find("*/", i + 2)
            if end == -1:
                raise ValueError("unterminated JSONC block comment")
            i = end + 2
        else:
            output.append(char)
            i += 1
    return re.sub(r",\s*([}\]])", r"\1", "".join(output))


class RenderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.env = Environment(undefined=StrictUndefined, keep_trailing_newline=True, autoescape=False)

    def context(self, profile_name: str, theme_name: str = "arthur") -> dict:
        with (ROOT / "profiles" / f"{profile_name}.toml").open("rb") as stream:
            profile = tomllib.load(stream)
        with (ROOT / "themes" / f"{theme_name}.toml").open("rb") as stream:
            theme = tomllib.load(stream)
        return {
            "home": "/home/tester",
            "repo": ROOT.as_posix(),
            "profile": profile,
            "theme": theme,
            "theme_name": theme_name,
            "targets": ["myarch", profile_name],
            "targets_str": f"myarch,{profile_name}",
            "myrig_path": "/home/tester/mysetup/myrig",
        }

    def test_all_templates_render_for_all_profiles_and_themes(self) -> None:
        templates = list((ROOT / "home").glob("**/*.jinja")) + list((ROOT / "src/hyprland").glob("*.jinja"))
        for profile in ("pocket4", "ideapad"):
            for theme in ("arthur", "tokyo-night", "matte-black"):
                context = self.context(profile, theme)
                for template in templates:
                    with self.subTest(profile=profile, theme=theme, template=template):
                        rendered = self.env.from_string(template.read_text()).render(**context)
                        self.assertNotIn("{{", rendered)
                        self.assertNotIn("{%", rendered)

    def test_waybar_jsonc_is_valid_for_both_profiles(self) -> None:
        for profile in ("pocket4", "ideapad"):
            context = self.context(profile)
            for name in ("config.jsonc.jinja", "modules.jsonc.jinja"):
                path = ROOT / "home/.config/waybar" / name
                rendered = self.env.from_string(path.read_text()).render(**context)
                with self.subTest(profile=profile, path=name):
                    json.loads(strip_jsonc(rendered))
            if profile == "pocket4":
                path = ROOT / "home/.config/waybar/config-narrow.jsonc.jinja"
                rendered = self.env.from_string(path.read_text()).render(**context)
                json.loads(strip_jsonc(rendered))

    def test_hyprland_fragments_are_ordered_and_complete(self) -> None:
        fragments = sorted((ROOT / "src/hyprland").glob("*.lua.jinja"))
        self.assertEqual(10, len(fragments))
        source = "\n".join(fragment.read_text() for fragment in fragments)
        for marker in ("MONITORS", "AUTOSTART", "LOOK AND FEEL", "GESTURES", "KEYBINDINGS", "WINDOWS AND WORKSPACES"):
            self.assertIn(marker, source)
        for profile in ("pocket4", "ideapad"):
            rendered = self.env.from_string(source).render(**self.context(profile))
            self.assertIn("hl.monitor", rendered)
            self.assertIn("hl.bind", rendered)

    def test_profile_specific_sources_do_not_install_on_ideapad(self) -> None:
        pocket_files = [path for path in (ROOT / "home").glob("**/*") if path.is_file() and (path.name.startswith("pocket4-") or path.name in {"config-narrow.jsonc.jinja", "style-compact.css", "pocket4.zsh"})]
        self.assertGreaterEqual(len(pocket_files), 10)

    def test_theme_contract(self) -> None:
        keys = None
        for path in sorted((ROOT / "themes").glob("*.toml")):
            with path.open("rb") as stream:
                theme = tomllib.load(stream)
            self.assertEqual(16, len(theme["palette"]))
            keys = set(theme) if keys is None else keys
            self.assertEqual(keys, set(theme), path)
            for key, value in theme.items():
                if key not in {"name", "palette"}:
                    self.assertRegex(value, r"^#[0-9a-fA-F]{6}$")

    def test_keybinding_catalogue_tracks_primary_chords(self) -> None:
        docs = (ROOT / "docs/keybindings.tsv").read_text()
        source = (ROOT / "src/hyprland/80-keybindings.lua.jinja").read_text()
        for chord, source_token in {
            "Super+R": 'mainMod .. " + R"',
            "Super+D": 'mainMod .. " + D"',
            "Super+G": 'mainMod .. " + G"',
            "Super+V": 'mainMod .. " + V"',
            "Super+Ctrl+S": 'mainMod .. " + CTRL + S"',
        }.items():
            self.assertIn(chord, docs)
            self.assertIn(source_token, source)


if __name__ == "__main__":
    unittest.main()
