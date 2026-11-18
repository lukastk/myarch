# Hyprpm plugin forks

myarch installs hyprexpo from upstream and hyprgrass from a fork under `lukastk` that builds a pocket4 branch with one code change. The fork is temporary: it has a concrete drop condition below, and every site to change carries the same `TODO(cleanup):` text (`grep -rn "TODO(cleanup): drop the lukastk/"`).

## Why a manifest change needs a fork

Two hyprpm behaviours (read from the v0.56.2 source, `hyprpm/src/core/PluginManager.cpp`) decide everything here:

- **hyprpm builds the pinned commit, not HEAD.** It reads the plugin list from the repository's HEAD `hyprpm.toml`, then resets the checkout to the `commit_pins` entry for the running Hyprland commit and builds that. A fix merged upstream reaches hyprpm users only once a pin points at it.
- **After an ABI change, one failed build blocks every plugin.** The ABI string includes library versions (`..._aq_0.15_hu_0.14_...`), so an aquamarine or hyprutils update changes it without a new Hyprland commit. `hyprpm update` then records the new ABI only if every plugin in every repository builds; until it does, `hyprpm reload` loads nothing. `hyprpm add` also refuses to run until that record matches.

## The forks

### `lukastk/hyprgrass` (touchscreen gestures, pocket4 only)

One change, on a branch:

**`pointer_emulation_mods`** (branch `pocket4-hyprland-0.57.2`, based on upstream's pin for Hyprland 0.57.2). While the named modifiers are held, a finger drives the mouse (press, drag, release), so Shift + finger drag selects text. Set in `src/hyprland/60-gestures.lua.jinja`.

`main`'s `hyprpm.toml` pins Hyprland 0.57.2 (`11cbc6c5…`) to the branch tip instead of upstream's `50e1660`, which the branch is based on.

- **On a Hyprland update:** upstream's pin for the new Hyprland commit builds WITHOUT the change. Rebase the branch onto that pin (name it after the new version), move the new pin to its tip, and rerun the installer. Missed, it fails loudly: Hyprland reports `pointer_emulation_mods` as an unknown option in `hyprctl configerrors`.
- **Drop when:** upstream has an equivalent option (none at the time of writing; nothing has been proposed upstream yet), or the Shift drag is no longer wanted.
- **History:** until 2026-11-18 the fork also carried a manifest cleanup (upstream removed the `[hyprgrass-pulse]`/`[hyprgrass-backlight]` entries) and a touch-down refocus fix (`refocus(touchPos)` instead of a bare `refocus()`, which sent `wl_pointer.motion` before every `wl_touch.down`); both are upstream now.
- **Related:** range-handle dragging also needs the Hyprland patch in `packages/hyprland/` (see its README): with only this fork, grabbing a handle still ends the drag.

## Keeping the forks current

A fork that misses upstream's newest pin builds the wrong source after the next Hyprland update. `.github/workflows/sync-plugin-forks.yml` calls GitHub's `merge-upstream` for the fork daily (and on manual dispatch). Fast-forwards and clean merges go through. A conflict fails the job, and usually means upstream changed the same manifest line as the fork, which is exactly when to re-check the drop condition.

The workflow needs the repository secret `PLUGIN_FORK_SYNC_TOKEN`, a token that can write to the fork, including their `.github/workflows` (upstream edits its own workflows, which the built-in `GITHUB_TOKEN` can never write). It is currently a copy of the account-wide `GITHUB_TOKEN` from 1Password, set without printing it via `secret get GITHUB_TOKEN | gh secret set PLUGIN_FORK_SYNC_TOKEN -R lukastk/myarch` (2026-09-17). That was a deliberate trade-off: no extra token to manage, against a secret in a public repository that can administer the whole account. Pull requests from other people's forks never receive secrets, and the job runs no third-party actions. To narrow it, replace the secret with a fine-grained token limited to `lukastk/hyprgrass`, with **Contents** and **Workflows** read/write. **Rotating `GITHUB_TOKEN` in 1Password does not update this copy.** Re-run the command above, or the job fails every day until you do.

GitHub Actions is **disabled on the fork**. Enabled, every sync would run upstream's own CI in the fork. Pull requests to upstream run their checks in the upstream repository, so the fork loses nothing.

## Switching a plugin back to upstream

1. In `install.py`, point the plugin URL back at upstream and delete its `TODO(cleanup)` line.
2. Delete the fork's entry in `.github/workflows/sync-plugin-forks.yml`, and the whole workflow once no forks remain.
3. Delete the fork's section here, and this file once no forks remain. Update the assertion in `test_every_plugin_fork_is_synced_from_upstream` in `tests/test_render.py`.
4. Rerun the installer. `configure_plugins` sees the installed repository's author differ from the declared URL's, then removes it, updates, and re-adds from upstream.
5. Archive the fork on GitHub.
