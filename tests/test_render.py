#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import runpy
import tempfile
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
                for name in ("config-narrow.jsonc.jinja", "config-tablet-landscape.jsonc.jinja"):
                    path = ROOT / "home/.config/waybar" / name
                    rendered = self.env.from_string(path.read_text()).render(**context)
                    with self.subTest(profile=profile, path=name):
                        json.loads(strip_jsonc(rendered))

    def test_fuzzel_ini_renders_as_a_parseable_config(self) -> None:
        source = ROOT / "home/.config/fuzzel/fuzzel.ini.jinja"
        installer = runpy.run_path((ROOT / "install.py").as_posix(), run_name="__not_main__")
        # fuzzel's ini parser rejects `;` comments with a hard syntax error, which
        # would take the whole launcher config down. The installer must stamp this
        # file with `#`, the way it already does for foot.
        self.assertEqual("#", installer["comment_prefix"](source))
        for profile in ("pocket4", "ideapad"):
            for theme in sorted(path.stem for path in (ROOT / "themes").glob("*.toml")):
                context = self.context(profile, theme)
                rendered = installer["add_disclaimer"](
                    source, self.env.from_string(source.read_text()).render(**context)
                )
                with self.subTest(profile=profile, theme=theme):
                    section = None
                    colours = 0
                    for line in rendered.splitlines():
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if line.startswith("[") and line.endswith("]"):
                            section = line[1:-1]
                            continue
                        self.assertIn("=", line)
                        key, value = line.split("=", 1)
                        self.assertRegex(key, r"^[a-z0-9-]+$")
                        if section == "colors":
                            # fuzzel takes RGBA as 8 hex digits and no leading '#'.
                            self.assertRegex(value, r"^[0-9a-f]{8}$")
                            colours += 1
                    self.assertEqual(11, colours)
                    self.assertIn(f"terminal={context['profile']['terminal']} -e", rendered)
                    # Touch dismissal: fuzzel's default `exclusive` focus locks
                    # keyboard focus to itself, so nothing outside can take it and
                    # a launcher opened by touch cannot be closed by touch.
                    self.assertIn("keyboard-focus=on-demand", rendered)

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

    def _run_monitor_fragment(self, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
        rendered = self.env.from_string((ROOT / "src/hyprland/00-monitors.lua.jinja").read_text()).render(**self.context("pocket4"))
        stub = 'hl = { monitor = function(m) print("scale=" .. tostring(m.scale) .. " transform=" .. tostring(m.transform)) end, device = function(d) end }\n'
        return subprocess.run([shutil.which("lua") or "lua", "-"], input=stub + rendered, env=env, capture_output=True, text=True)

    def test_pocket4_monitor_scale_survives_config_reloads(self) -> None:
        # The monitor fragment is re-evaluated on every Hyprland config reload;
        # its scale must come from tablet mode's state, not a literal.
        if shutil.which("lua") is None:
            self.skipTest("no lua interpreter")
        with tempfile.TemporaryDirectory() as temporary:
            cache = Path(temporary) / "cache"
            state = cache / "pocket4/tablet-mode"
            base = {"PATH": os.environ["PATH"], "HOME": temporary, "XDG_CACHE_HOME": cache.as_posix()}

            missing = self._run_monitor_fragment(base)
            self.assertEqual(0, missing.returncode, missing.stderr)
            self.assertEqual("scale=1.6 transform=3", missing.stdout.strip())

            state.parent.mkdir(parents=True)
            for content, expected in (("on\n", "scale=2.0"), ("off\n", "scale=1.6")):
                state.write_text(content)
                result = self._run_monitor_fragment(base)
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual(f"{expected} transform=3", result.stdout.strip())

            # Same path rule as pocket4-tablet-mode's ${XDG_CACHE_HOME:-$HOME/.cache}.
            home_state = Path(temporary) / ".cache/pocket4/tablet-mode"
            home_state.parent.mkdir(parents=True)
            home_state.write_text("on\n")
            empty = self._run_monitor_fragment(dict(base, XDG_CACHE_HOME=""))
            self.assertEqual("scale=2.0 transform=3", empty.stdout.strip(), empty.stderr)

            state.write_text("maybe\n")
            broken = self._run_monitor_fragment(base)
            self.assertNotEqual(0, broken.returncode)
            self.assertIn("must be 'on' or 'off'", broken.stderr)

        lua = (ROOT / "src/hyprland/00-monitors.lua.jinja").read_text()
        script = (ROOT / "home/.mybin/pocket4-tablet-mode").read_text()
        desktop = re.search(r"^SCALE_DESKTOP=([0-9.]+)", script, re.M).group(1)
        tablet = re.search(r"^SCALE_TABLET=([0-9.]+)", script, re.M).group(1)
        self.assertEqual(float(desktop), float(re.search(r"POCKET4_SCALE_DESKTOP\s*=\s*([0-9.]+)", lua).group(1)))
        self.assertEqual(float(tablet), float(re.search(r"POCKET4_SCALE_TABLET\s*=\s*([0-9.]+)", lua).group(1)))
        self.assertIn('STATE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/pocket4"', script)
        self.assertIn('STATE="$STATE_DIR/tablet-mode"', script)
        ideapad = self.env.from_string(lua).render(**self.context("ideapad"))
        self.assertNotIn("tablet-mode", ideapad)

    def test_pocket4_runtime_monitor_changes_are_applied_and_verified(self) -> None:
        # On Hyprland 0.56 a runtime hl.monitor() only registers the rule ("ok",
        # nothing changes) until hl.dsp.force_renderer_reload() is DISPATCHED.
        # Measured on pocket4 2026-09-14: without it tablet mode never changed the
        # scale and pocket4-display never rotated. Both must also check the panel
        # really got there.
        for name, scale_var, transform_var in (("pocket4-tablet-mode", "$s", "$t"), ("pocket4-display", "$s", "$t")):
            with self.subTest(script=name):
                script = (ROOT / "home/.mybin" / name).read_text()
                self.assertIn("set -euo pipefail", script)
                lines = script.splitlines()
                evals = [i for i, line in enumerate(lines) if "hyprctl eval" in line and "hl.monitor(" in line]
                self.assertTrue(evals)
                for index in evals:
                    rest = "\n".join(lines[index:index + 16])
                    self.assertIn("hyprctl dispatch 'hl.dsp.force_renderer_reload()'", rest)
                    self.assertIn(f'wait_for_panel "{scale_var}" "{transform_var}"', rest)
                    # A reload dispatched through eval would be built and discarded.
                    self.assertNotIn("hyprctl eval 'hl.dsp.force_renderer_reload", rest)
                self.assertRegex(script, r"wait_for_panel\(\) \{[\s\S]*?return 1\n\}")

    def test_three_finger_up_is_touchscreen_only(self) -> None:
        template = (ROOT / "src/hyprland/60-gestures.lua.jinja").read_text()
        pocket = self.env.from_string(template).render(**self.context("pocket4"))
        ideapad = self.env.from_string(template).render(**self.context("ideapad"))

        self.assertIn('fingers = 3, direction = "up"', pocket)
        self.assertIn('fingers = 4, direction = "up"', pocket)
        self.assertNotIn('direction = "up"', ideapad)

    def test_profile_specific_sources_do_not_install_on_ideapad(self) -> None:
        pocket_files = [path for path in (ROOT / "home").glob("**/*") if path.is_file() and (path.name.startswith("pocket4-") or path.name in {"config-narrow.jsonc.jinja", "config-tablet-landscape.jsonc.jinja", "style-compact.css", "pocket4.zsh"})]
        self.assertGreaterEqual(len(pocket_files), 10)

    def test_waybar_restart_has_one_serialized_authority(self) -> None:
        display = (ROOT / "home/.mybin/pocket4-display").read_text()
        restart = (ROOT / "home/.mybin/restart-bar").read_text()
        self.assertNotIn("pkill -x waybar", display)
        self.assertIn('"$HOME/.mybin/restart-bar" --layout', display)
        self.assertIn("flock 9", restart)
        self.assertIn('9>&-', restart)
        self.assertIn("expected one waybar process", restart)

    def test_pocket_display_couples_monitor_and_touch_transforms(self) -> None:
        display = (ROOT / "home/.mybin/pocket4-display").read_text()
        self.assertRegex(display, r'hyprctl eval "hl\.monitor\(.*transform = \$t')
        self.assertRegex(display, r'hyprctl eval "hl\.device\(.*transform = \$t')

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
            "Super+Ctrl+I": 'mainMod .. " + CTRL + I"',
        }.items():
            self.assertIn(chord, docs)
            self.assertIn(source_token, source)

    def _run_app_flags(self, config_home: Path, *args: str) -> subprocess.CompletedProcess[str]:
        # XDG_STATE_HOME too: the generator also writes desktop-mode, and the real
        # one is watched by mysystem in the running Obsidian.
        env = dict(os.environ, XDG_CONFIG_HOME=config_home.as_posix(), XDG_STATE_HOME=(config_home / "state").as_posix())
        return subprocess.run([(ROOT / "home/.mybin/myarch-app-flags").as_posix(), *args], env=env, capture_output=True, text=True)

    @staticmethod
    def _launcher_flags(path: Path) -> list[str]:
        # The filter Arch's /usr/bin/brave and /usr/bin/obsidian apply before
        # passing each line as an argument: skip blank and #-comment lines.
        return [line for line in path.read_text().splitlines() if not re.match(r"^\s*(#|$)", line)]

    def test_app_flags_follow_the_desktop_mode(self) -> None:
        blink = "--blink-settings=availablePointerTypes=2,primaryPointerType=2,availableHoverTypes=1,primaryHoverType=1"
        touch_editing = "--enable-features=TouchTextEditingRedesign"
        with tempfile.TemporaryDirectory() as temporary:
            config_home = Path(temporary)
            (config_home / "myarch").mkdir()
            shutil.copy(ROOT / "home/.config/myarch/app-flags.toml", config_home / "myarch/app-flags.toml")
            brave, obsidian = config_home / "brave-flags.conf", config_home / "obsidian-flags.conf"
            # A pre-existing symlink (the old installer linked brave-flags.conf) is replaced, not followed.
            decoy = config_home / "decoy.conf"
            decoy.write_text("--must-not-change\n")
            brave.symlink_to(decoy)

            laptop = self._run_app_flags(config_home, "write", "--mode", "laptop")
            self.assertEqual(0, laptop.returncode, laptop.stderr)
            self.assertEqual(sorted([brave.as_posix(), obsidian.as_posix()]), sorted(laptop.stdout.split()))
            self.assertFalse(brave.is_symlink())
            self.assertEqual("--must-not-change\n", decoy.read_text())
            self.assertEqual(["--ozone-platform-hint=auto", touch_editing], self._launcher_flags(brave))
            self.assertEqual([touch_editing], self._launcher_flags(obsidian))
            self.assertIn("NOTE! This file was generated by myarch; edit its source instead", brave.read_text())
            desktop_mode = config_home / "state/myarch/desktop-mode"
            self.assertEqual("laptop\n", desktop_mode.read_text())
            self.assertNotIn(desktop_mode.as_posix(), laptop.stdout)  # state, not an installed file

            tablet = self._run_app_flags(config_home, "write", "--mode", "tablet")
            self.assertEqual(0, tablet.returncode, tablet.stderr)
            self.assertEqual(["--ozone-platform-hint=auto", touch_editing, blink], self._launcher_flags(brave))
            # Obsidian switches at runtime from desktop-mode (mysystem), never by
            # launch flag: a launch flag cannot be undone without a restart.
            self.assertEqual([touch_editing], self._launcher_flags(obsidian))
            self.assertEqual("tablet\n", desktop_mode.read_text())

            # Back to laptop drops the touch flags again.
            self.assertEqual(0, self._run_app_flags(config_home, "write", "--mode", "laptop").returncode)
            self.assertEqual(["--ozone-platform-hint=auto", touch_editing], self._launcher_flags(brave))
            self.assertEqual("laptop\n", desktop_mode.read_text())

    def test_app_flags_fail_loudly_on_bad_input(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            config_home = Path(temporary)
            (config_home / "myarch").mkdir()
            source = config_home / "myarch/app-flags.toml"
            self.assertNotEqual(0, self._run_app_flags(config_home, "write", "--mode", "laptop").returncode)  # no source
            shutil.copy(ROOT / "home/.config/myarch/app-flags.toml", source)
            self.assertNotEqual(0, self._run_app_flags(config_home, "write", "--mode", "desk").returncode)
            source.write_text('[tablet]\nflags = []\n[apps.brave]\nfile = "brave-flags.conf"\nalways = []\ntablet = true\n')
            self.assertNotEqual(0, self._run_app_flags(config_home, "write", "--mode", "tablet").returncode)
            source.write_text('[tablet]\nflags = ["--x"]\n[apps.brave]\nfile = "../escape-flags.conf"\nalways = []\ntablet = true\n')
            self.assertNotEqual(0, self._run_app_flags(config_home, "write", "--mode", "tablet").returncode)
            self.assertFalse((config_home.parent / "escape-flags.conf").exists())

    def test_pocket4_tablet_mode_writes_app_flags_before_changing_mode(self) -> None:
        script = (ROOT / "home/.mybin/pocket4-tablet-mode").read_text()
        on = re.search(r"^on\(\)\s*\{(.*)\}$", script, re.M)
        off = re.search(r"^off\(\)\s*\{(.*)\}$", script, re.M)
        self.assertIsNotNone(on)
        self.assertIsNotNone(off)
        for body, mode in ((on.group(1), "tablet"), (off.group(1), "laptop")):
            flags = body.index(f'"$APP_FLAGS" write --mode {mode}')
            self.assertLess(flags, body.index("set_scale"))
            self.assertLess(flags, body.index('> "$STATE"'))
        self.assertIn('APP_FLAGS="$HOME/.mybin/myarch-app-flags"', script)

    def test_installer_generates_app_flags_instead_of_linking_them(self) -> None:
        self.assertFalse((ROOT / "home/.config/brave-flags.conf").exists())
        self.assertFalse((ROOT / "home/.config/obsidian-flags.conf").exists())
        installer = (ROOT / "install.py").read_text()
        self.assertIn("installed.extend(write_app_flags(profile_name))", installer)
        self.assertIn('(HOME / ".mybin/pocket4-tablet-mode").as_posix(), "get"', installer)
        module = runpy.run_path((ROOT / "install.py").as_posix(), run_name="__not_main__")
        self.assertEqual("laptop", module["app_flags_mode"]("ideapad"))
        generator = (ROOT / "home/.mybin/myarch-app-flags").read_text()
        # The installer's stale-file cleanup recognises owned files by this text.
        self.assertIn(f'DISCLAIMER = "{module["DISCLAIMER"]}"', generator)

    def test_plugin_repositories_are_reinstalled_when_their_author_changes(self) -> None:
        module = runpy.run_path((ROOT / "install.py").as_posix(), run_name="__not_main__")
        configure_plugins = module["configure_plugins"]

        def listing(repositories: dict[str, str]) -> str:
            # Shaped like real `hyprpm list` output, colour codes included.
            return "".join(
                f"\x1b[0m→\x1b[0m Repository {name} (by {author}):\n  │ Plugin {name}\n  └─ enabled: \x1b[32mtrue\n\x1b[0m\n"
                for name, author in repositories.items()
            )

        def install(profile_name: str, repositories: dict[str, str]) -> list[list[str]]:
            with (ROOT / "profiles" / f"{profile_name}.toml").open("rb") as stream:
                profile = tomllib.load(stream)
            calls: list[list[str]] = []

            def fake_run(argv: list[str], *, check: bool = True, capture: bool = False, env: dict | None = None):
                calls.append(argv)
                if argv[:2] == ["hyprpm", "remove"]:
                    del repositories[argv[2].split("/")[1]]
                elif argv[:2] == ["hyprpm", "add"]:
                    repositories[argv[2].split("/")[-1]] = argv[2].split("/")[-2]
                stdout = listing(repositories) if argv == ["hyprpm", "list"] else ""
                return subprocess.CompletedProcess(argv, 0, stdout=stdout)

            configure_plugins.__globals__["run"] = fake_run
            configure_plugins(profile, {})
            return calls

        repositories = {"hyprgrass": "horriblename", "hyprexpo": "sandwichfarm"}
        calls = install("pocket4", repositories)
        update = calls.index(["hyprpm", "update"])
        for stale, url in (
            ("horriblename/hyprgrass", "https://github.com/lukastk/hyprgrass"),
            ("sandwichfarm/hyprexpo", "https://github.com/lukastk/hyprexpo"),
        ):
            # A stale repository goes before the update it would otherwise fail.
            self.assertLess(calls.index(["hyprpm", "remove", stale]), update)
            self.assertLess(update, calls.index(["hyprpm", "add", url]))
        self.assertEqual({"hyprgrass": "lukastk", "hyprexpo": "lukastk"}, repositories)

        rerun = install("pocket4", repositories)
        self.assertEqual([], [argv for argv in rerun if argv[1] in ("remove", "add")])
        self.assertIn(["hyprpm", "enable", "hyprgrass"], rerun)

        ideapad = install("ideapad", {"hyprexpo": "sandwichfarm"})
        self.assertIn(["hyprpm", "add", "https://github.com/lukastk/hyprexpo"], ideapad)
        self.assertFalse([argv for argv in ideapad if "hyprgrass" in " ".join(argv)])

    def test_every_plugin_fork_is_synced_from_upstream(self) -> None:
        # A fork that stops receiving upstream's commit pins builds the wrong
        # source after the next Hyprland update.
        forks = set(re.findall(r'"https://github\.com/(lukastk/[\w-]+)"', (ROOT / "install.py").read_text()))
        self.assertEqual({"lukastk/hyprexpo", "lukastk/hyprgrass"}, forks)
        workflow = (ROOT / ".github/workflows/sync-plugin-forks.yml").read_text()
        for fork in forks:
            self.assertIn(f"repo: {fork}\n", workflow)
        self.assertIn("timeout-minutes:", workflow)

    def test_audio_input_picker_uses_pipewire_sources(self) -> None:
        picker_path = ROOT / "home/.mybin/audio-input"
        picker = picker_path.read_text()
        self.assertTrue(picker_path.stat().st_mode & 0o100)
        self.assertIn('["pactl", "--format=json", "list", "sources"]', picker)
        self.assertIn('["pactl", "set-default-source", selected]', picker)
        self.assertIn('"--with-nth=1"', picker)
        self.assertIn("source['name'] == current", picker)
        self.assertNotIn("shell=True", picker)
        compile(picker, picker_path.as_posix(), "exec")

    def test_keyboard_backlight_uses_led_class_and_preserves_pocket_firmware_truth(self) -> None:
        helper_path = ROOT / "home/.mybin/keyboard-backlight"
        helper = helper_path.read_text()
        self.assertTrue(helper_path.stat().st_mode & 0o100)
        self.assertNotIn("shell=True", helper)
        self.assertIn('POCKET4_KEYBOARD = ("258a", "000c")', helper)
        self.assertIn('name.endswith(":kbd_backlight")', helper)
        self.assertIn('["brightnessctl", "--class", "leds", "--device", device.name', helper)

        namespace = runpy.run_path(helper_path)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            led = root / "platform::kbd_backlight"
            led.mkdir()
            (led / "brightness").write_text("1\n")
            (led / "max_brightness").write_text("2\n")
            devices = namespace["discover"](root)
        self.assertEqual(1, len(devices))
        self.assertEqual("platform::kbd_backlight", devices[0].name)
        self.assertEqual("low", namespace["level_name"](1, 2))
        self.assertEqual(2, namespace["parse_level"]("100%", 2))
        with self.assertRaises(ValueError):
            namespace["parse_level"]("3", 2)

        bindings = (ROOT / "src/hyprland/80-keybindings.lua.jinja").read_text()
        self.assertIn('hl.bind("XF86KbdBrightnessUp"', bindings)
        self.assertIn('hl.bind("XF86KbdLightOnOff"', bindings)
        router = (ROOT / "home/.mybin/myarch").read_text()
        self.assertIn('HOME / ".mybin/keyboard-backlight"', router)

        rules = (ROOT / "system/udev/90-myarch-brightness.rules.in").read_text()
        self.assertEqual(3, rules.count("@USER@"))
        self.assertIn('KERNEL=="*:kbd_backlight"', rules)
        installer = (ROOT / "install.py").read_text()
        self.assertIn('configure_brightness_access()', installer)
        self.assertIn('["sudo", "chown", username, attribute.as_posix()]', installer)


    def test_pocket_thermal_picker_uses_fzf_and_is_profile_scoped(self) -> None:
        picker_path = ROOT / "home/.mybin/pocket4-thermal-mode"
        picker = picker_path.read_text()
        self.assertTrue(picker_path.stat().st_mode & 0o100)
        self.assertIn("pick) pick", picker)
        self.assertIn("--prompt='power> '", picker)
        self.assertIn("--with-nth=1", picker)
        self.assertIn('is_mode "$selected"', picker)
        self.assertIn('[ "$selected" = "$current" ] || set_mode "$selected"', picker)

        binding_template = (ROOT / "src/hyprland/80-keybindings.lua.jinja").read_text()
        rules_template = (ROOT / "src/hyprland/90-window-rules.lua.jinja").read_text()
        pocket_binding = self.env.from_string(binding_template).render(**self.context("pocket4"))
        ideapad_binding = self.env.from_string(binding_template).render(**self.context("ideapad"))
        pocket_rules = self.env.from_string(rules_template).render(**self.context("pocket4"))
        ideapad_rules = self.env.from_string(rules_template).render(**self.context("ideapad"))
        self.assertIn('mainMod .. " + CTRL + P"', pocket_binding)
        self.assertIn("pocket4-thermal-mode pick", pocket_binding)
        self.assertNotIn('mainMod .. " + CTRL + P"', ideapad_binding)
        self.assertIn("^thermal-mode-pick$", pocket_rules)
        self.assertNotIn("^thermal-mode-pick$", ideapad_rules)

    def test_monospace_surfaces_use_ioskeley(self) -> None:
        family = "IoskeleyMonoTerm Nerd Font Mono"
        surfaces = [
            ROOT / "home/.config/foot/foot.ini.jinja",
            ROOT / "home/.config/kitty/kitty.conf.jinja",
            ROOT / "home/.config/mako/config.jinja",
            ROOT / "home/.config/hypr/hyprlock.conf.jinja",
            ROOT / "home/.config/waybar/style.css.jinja",
        ]
        for surface in surfaces:
            with self.subTest(surface=surface):
                self.assertIn(family, surface.read_text())
                self.assertNotIn("JetBrainsMono", surface.read_text())
        installer = (ROOT / "install.py").read_text()
        self.assertIn(f'MONO_FONT_FAMILY = "{family}"', installer)
        self.assertIn("require_mono_font()", installer)
        self.assertNotIn("ttf-jetbrains-mono-nerd", (ROOT / "install.sh").read_text())

    def test_voxtype_config_and_adapter_preserve_dictation_contract(self) -> None:
        config_template = ROOT / "home/.config/voxtype/config.toml.jinja"
        adapter_template = ROOT / "home/.mybin/voxtype-key.jinja"
        for profile, expected_volume, expected_source in (
            ("pocket4", "25%", "alsa_input.pci-0000_c5_00.6.analog-stereo"),
            ("ideapad", "unchanged", ""),
        ):
            context = self.context(profile)
            rendered_config = self.env.from_string(config_template.read_text()).render(**context)
            config = tomllib.loads(rendered_config)
            with self.subTest(profile=profile):
                self.assertEqual("parakeet", config["engine"])
                self.assertFalse(config["hotkey"]["enabled"])
                self.assertFalse(config["output"]["fallback_to_clipboard"])
                self.assertEqual(["wtype"], config["output"]["driver_order"])
                self.assertIsInstance(config["audio"]["feedback"]["volume"], float)
                self.assertIn("cleanup", config["profiles"])
                self.assertIn("raw", config["profiles"])

                adapter = self.env.from_string(adapter_template.read_text()).render(**context)
                self.assertIn(f'CAPTURE_VOLUME = "{expected_volume}"', adapter)
                self.assertIn(f'CAPTURE_SOURCE = "{expected_source}"', adapter)
                self.assertIn('[VOXTYPE, "record", "start"]', adapter)
                self.assertIn('[VOXTYPE, "record", command]', adapter)
                self.assertIn('HOLD_THRESHOLD_SECONDS = 0.350', adapter)
                self.assertIn("orphan_release_at", adapter)
                self.assertIn('["systemctl", "--user", "restart", "voxtype.service"]', adapter)
                self.assertNotIn("shell=True", adapter)
                compile(adapter, adapter_template.as_posix(), "exec")

    def test_dictation_gain_compensation_is_scoped_to_its_measured_source(self) -> None:
        """The 25% is calibration for the Pocket's built-in mic, not a policy.

        pactl percentages are cubic, so 25% is -36.12 dB. Applied to whatever
        source happens to be selected it silently destroys mics with no headroom
        to spare: measured on pocket4 2026-09-04, speech into the Nothing Ear (a)
        peaked at 20235/32768 at 100% and at 39 at 25%. And because the restore
        re-resolved @DEFAULT_SOURCE@ instead of naming the source it attenuated,
        a headset that disconnected mid-dictation kept the attenuation - which
        WirePlumber then persisted across reboots.
        """
        adapter = (ROOT / "home/.mybin/voxtype-key.jinja").read_text()

        # Every volume call names its source; none re-resolve the default.
        # (Comments may still discuss @DEFAULT_SOURCE@ - the code may not use it.)
        code = "\n".join(
            line for line in adapter.splitlines() if not line.lstrip().startswith("#")
        )
        self.assertNotIn("@DEFAULT_SOURCE@", code)
        self.assertIn("def get_source_volume(source: str) -> str:", adapter)
        self.assertIn("def set_source_volume(source: str, value: str) -> None:", adapter)
        self.assertIn('["pactl", "get-source-volume", source]', adapter)
        self.assertIn('["pactl", "set-source-volume", source, value]', adapter)

        # The transaction runs only for the source the profile measured it for,
        # and the restore is addressed to the source recorded in the state.
        self.assertIn("if default_source() == CAPTURE_SOURCE:", adapter)
        self.assertIn('"volume_source": volume_source,', adapter)
        self.assertIn('source = state.get("volume_source")', adapter)
        self.assertIn("missing attenuated source in Voxtype adapter state", adapter)

        for profile_name in ("pocket4", "ideapad"):
            with (ROOT / "profiles" / f"{profile_name}.toml").open("rb") as stream:
                dictation = tomllib.load(stream)["dictation"]
            with self.subTest(profile=profile_name):
                self.assertIn("source_volume_source", dictation)
                if dictation["source_volume"] == "unchanged":
                    self.assertEqual("", dictation["source_volume_source"])
                else:
                    self.assertTrue(dictation["source_volume_source"])

        # A profile may not ask for an attenuation without naming its target.
        installer = runpy.run_path((ROOT / "install.py").as_posix(), run_name="__not_main__")
        validate = installer["validate_dictation"]
        validate(Path("ok.toml"), {"dictation": {"source_volume": "25%", "source_volume_source": "mic"}})
        validate(Path("ok.toml"), {"dictation": {"source_volume": "unchanged", "source_volume_source": ""}})
        for bad in (
            {"source_volume": "25%", "source_volume_source": ""},
            {"source_volume": "unchanged", "source_volume_source": "mic"},
            {"source_volume": "25"},
        ):
            with self.subTest(bad=bad), self.assertRaises(SystemExit):
                validate(Path("bad.toml"), {"dictation": bad})

    def test_voxtype_replaces_mydictation_runtime_ownership(self) -> None:
        for profile_name in ("pocket4", "ideapad"):
            with (ROOT / "profiles" / f"{profile_name}.toml").open("rb") as stream:
                profile = tomllib.load(stream)
            self.assertTrue(profile["voxtype"])
            self.assertNotIn("mydictation", profile)
        self.assertFalse((ROOT / "home/.config/mydictation/config.toml.jinja").exists())
        service = (ROOT / "home/.config/systemd/user/voxtype.service").read_text()
        self.assertIn("ExecStart=%h/.mybin/voxtype-daemon", service)
        cleanup = (ROOT / "home/.mybin/voxtype-cleanup").read_text()
        compile(cleanup, "voxtype-cleanup", "exec")
        router = (ROOT / "home/.mybin/myarch").read_text()
        self.assertIn('"sesh", "voxtype"', router)
        self.assertNotIn('"sesh", "mydictation-key"', router)
        self.assertIn("skip hyprland config errors: no running instance", router)
        self.assertIn('["pgrep", "-x", "Hyprland"]', router)
        installer = (ROOT / "install.py").read_text()
        self.assertIn('VOXTYPE_RELEASE = "1.0.0-rc2"', installer)
        self.assertIn("425d650273220382f73a3bb4f8a563e0769f1c694eabb7c82701a919f44a689b", installer)
        self.assertIn('start_external(profile, environment)', installer)
        self.assertIn('if environment is not None:', installer)
        self.assertNotIn('["systemctl", "--user", "enable", "--now", "voxtype.service"]', installer)


if __name__ == "__main__":
    unittest.main()
