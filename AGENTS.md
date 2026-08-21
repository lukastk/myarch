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
- `install.py` owns rendering, state migration, system integration, plugins, and coherent reload.
- Myrig owns fleet composition, clone order, private wallpapers, RustDesk policy, Pocket system provisioning, server mode, backups, Sesh, and subswitcher.

## Required checks

Run before every commit:

```bash
./scripts/test
./scripts/check-secrets.py
git diff --check
```

For Pocket-facing UI changes, also test all four orientation/scale states and restore landscape desktop mode. Check `hyprctl configerrors`, `journalctl --user -t pocket4-waybar`, and actual layer dimensions. Test touch on real hardware when hit targets or gestures change.

## Commits

Every commit message must be a prompt another agent can use to recreate the work.

## Temporary migrations

Any explicitly agreed temporary path must carry the exact `TODO(cleanup):` tag at every cleanup site and state a concrete removal event/date.