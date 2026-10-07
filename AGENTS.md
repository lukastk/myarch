# myarch development guide

myarch is an Arch Linux/Hyprland desktop repository installed on Pocket 4 and IdeaPad. Deployments to either profile must remain explicit.

## Non-negotiable behavior

- Changes are additive in capability. Do not delete workspace, Sesh/SST, dictation, Pocket display/touch/tablet/OSK/thermal, brightness, display-mode, idle/lock, wallpaper, clipboard, font, or session-environment behavior to simplify presentation.
- Existing backend commands remain authoritative. UI code delegates; it does not reimplement hardware state.
- `pocket4-display` must change monitor and touchscreen transforms together.
- Pocket bar layouts must fit logical widths 1600, 1280, 1000, and 800 without oversized surfaces or shifted hit targets.
- Hyprpm plugins are ABI-locked to the running Hyprland commit. Rebuild them after every compositor update.
- Missing required state fails loudly. Do not add defensive fallback values that hide broken integrations.
- Never interpolate paths or other external strings into shell commands that are reparsed. Pass paths as argv.

## Ownership

- `src/hyprland/` is the modular source. The installer concatenates its ordered fragments into one Lua parser unit so lexical scope and behavior stay identical.
- `home/` owns user configuration and commands.
- `profiles/` owns explicit hardware contracts; never autodetect profile.
- `themes/` must all expose the exact same semantic key set.
- `packages/` holds myarch-patched builds of Arch packages. A profile lists the ones it uses in `[packages] patched`; `install.sh` keeps those out of its `pacman -S` and runs `packages/install-patched` for each, which fails loudly once the repositories move past the release a patch was made for. Each package has a README saying why, how to rebase, and when to drop it.
- `install.sh` is the entry point: the Arch-only guard, argument parsing, the complete pacman package set, and the paru AUR packages (`ticktick`, `voxtype-bin`). Add desktop packages there. It then hands off to `install.py`.
- `install.py` owns rendering, state migration, system integration, plugins, and coherent reload.
- Myrig owns fleet composition, clone order, private wallpapers, RustDesk policy, Pocket system provisioning, server mode, backups, Sesh, and subswitcher.

## Installing

```bash
./install.sh --profile pocket4|ideapad [--theme <name>] [--config-only] [--skip-runtime]
```

`--profile` is required. myrig's `myarch` target runs `install.sh --profile <machine>` on each Arch machine during `myrig-reinstall`, so a fleet update redeploys myarch. `--config-only` renders and reloads without package, service, plugin, or external-integration work. `--skip-runtime` is for provisioning without a Hyprland session; plugin work is deferred until the installer is rerun inside Hyprland.

## Required checks

Run before every commit:

```bash
./scripts/test
git diff --check
```

For Pocket-facing UI changes, also test all four orientation/scale states and restore landscape desktop mode. Check `hyprctl configerrors`, `journalctl --user -t pocket4-waybar`, and actual layer dimensions. Test touch on real hardware when hit targets or gestures change.

## Commits

Every commit message must be a prompt another agent can use to recreate the work.

## Temporary migrations

Any explicitly agreed temporary path must carry the exact `TODO(cleanup):` tag at every cleanup site and state a concrete removal event/date.

## Scheduled review: carried patches and upstream reports (due 2026-11-02)

Since 2026-09-17, hyprexpo and hyprgrass have been installed from temporary `lukastk` forks. `.github/workflows/sync-plugin-forks.yml` keeps them current, using `PLUGIN_FORK_SYNC_TOKEN`, a copy of the account-wide GitHub token. Why each fork exists and when it can go: `docs/plugin-forks.md`. The hyprgrass fork also carries two code changes for touch selection (branch `pocket4-hyprland-0.56.2`), and pocket4 runs a patched Hyprland from `packages/hyprland/`. Reporting either fix upstream was deliberately deferred to this review.

**On or after 2026-11-02, bring this review up with Lukas near the start of any session in this repo**, whatever the session is about, until he has decided and this section has been updated or removed. Before that date, raise it only if the sync job is failing, the work touches hyprpm plugins, or Hyprland is being updated (the hyprgrass branch and the Hyprland patch both need rebasing then).

For the review:
- Run each fork's drop check from `docs/plugin-forks.md` and say which forks can already go back to upstream.
- Summarise the recent sync runs (`gh run list -R lukastk/myarch --workflow sync-plugin-forks.yml`): how often they failed, and why.
- Ask whether to keep the forks and the automation, narrow the token to a fine-grained one, or drop them.
- Check whether upstream hyprgrass has the touch-down refocus fix and whether Hyprland's `simulateMouseMovement` skips touch input on its own (checks in `docs/plugin-forks.md` and `packages/hyprland/README.md`); say what can be dropped.
- Ask whether to report upstream: the hyprgrass touch-down fix, the Hyprland patch, and whether to offer `pointer_emulation_mods` to hyprgrass. Never file anything upstream without his explicit go-ahead.
- Decision notes are in the myvault pad `pad/Revisit myarch's hyprpm plugin forks.md`. The matching task (📅 2026-11-02) is in the planner note `pln/2026-09-17.md`; mark it done when the review is finished.

## Desktop/test safety

- Coordinate compositor restarts with Lukas; they close the desktop session. Never interrupt a debugger attached to live Hyprland: SIGINT can be delivered on detach and kill the compositor. Prefer non-ptrace diagnostics; recheck the running build before using memory offsets.
- Never capture real password keycodes with WAYLAND_DEBUG or evdev logging. Coordinate lock/DPMS/suspend tests and do not bypass server-mode suspend inhibition without agreement. Preserve delayed power-limit restoration; do not disable systemd's freezer to hide resume lag.
- Rediscover the active desktop session and `HYPRLAND_INSTANCE_SIGNATURE` after restarts; historical PIDs/session IDs are not reusable.
- For speech tests, play an audible cue through the earbuds, give a scoreable sentence, and wait for Lukas's go. Target a background task by its ID, not `pkill -f <script>` (which can kill the harness shell).
- `myrig-reinstall` restarts supervisord and can kill the Sesh work tmux server and its threads; coordinate fleet reinstalls, and check for one when diagnosing a Pocket session crash.

## Task-to-reference routing (on demand only)

Read the relevant reference/section for the task, not this entire list at startup.

| Task | Reference |
| --- | --- |
| Installer/rendering, ownership, source layout | [Architecture](docs/architecture.md); [commands and layout](README.md) |
| Pocket display/tablet/bar/touch changes | [Pocket contract and validation](docs/pocket4.md); [feature parity](docs/feature-parity.md); explicit profiles in `profiles/` |
| Shortcuts and actions | [Binding catalogue](docs/keybindings.tsv) |
| Hyprland updates, plugin ABI/pins, fork review | [Plugin forks](docs/plugin-forks.md); [patched Hyprland](packages/hyprland/README.md) |
| Trackpad tuning, launcher focus/latency, plugin failures, touch selection, debugger recovery, Bluetooth/dictation, lock/wake, audio routing | [Desktop investigation topic index](docs/desktop-investigations.md#topic-index): select the relevant dated section; later findings supersede earlier diagnoses |

Keep `AGENTS.local.md` a compact live trap digest. Put detailed evidence/history in ordinary topic docs, not eager imports. `CLAUDE.md` imports only this guide and that digest; preserve those entry points for Pi/Claude/Codex.
