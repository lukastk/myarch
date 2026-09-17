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

## Scheduled review: plugin forks and their sync (due 2026-11-02)

Since 2026-09-17, hyprexpo and hyprgrass have been installed from temporary `lukastk` forks. `.github/workflows/sync-plugin-forks.yml` keeps them current, using `PLUGIN_FORK_SYNC_TOKEN`, a copy of the account-wide GitHub token. Why each fork exists and when it can go: `docs/plugin-forks.md`.

**On or after 2026-11-02, bring this review up with Lukas near the start of any session in this repo**, whatever the session is about, until he has decided and this section has been updated or removed. Before that date, raise it only if the sync job is failing or the work touches hyprpm plugins.

For the review:
- Run each fork's drop check from `docs/plugin-forks.md` and say which forks can already go back to upstream.
- Summarise the recent sync runs (`gh run list -R lukastk/myarch --workflow sync-plugin-forks.yml`): how often they failed, and why.
- Ask whether to keep the forks and the automation, narrow the token to a fine-grained one, or drop them.
- Decision notes are in the myvault pad `pad/Revisit myarch's hyprpm plugin forks.md`. The matching task (📅 2026-11-02) is in the planner note `pln/2026-09-17.md`; mark it done when the review is finished.
