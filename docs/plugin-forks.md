# Hyprpm plugin forks

myarch installs both hyprpm plugins from forks under `lukastk`. hyprexpo's fork is one manifest commit on top of upstream; hyprgrass's also builds a pocket4 branch with two code changes. They are temporary: every fork has a concrete drop condition below, and every site to change carries the same `TODO(cleanup):` text (`grep -rn "TODO(cleanup): drop the lukastk/"`).

## Why a manifest change needs a fork

Two hyprpm behaviours (read from the v0.56.2 source, `hyprpm/src/core/PluginManager.cpp`) decide everything here:

- **hyprpm builds the pinned commit, not HEAD.** It reads the plugin list from the repository's HEAD `hyprpm.toml`, then resets the checkout to the `commit_pins` entry for the running Hyprland commit and builds that. A fix merged upstream reaches hyprpm users only once a pin points at it.
- **After an ABI change, one failed build blocks every plugin.** The ABI string includes library versions (`..._aq_0.15_hu_0.14_...`), so an aquamarine or hyprutils update changes it without a new Hyprland commit. `hyprpm update` then records the new ABI only if every plugin in every repository builds; until it does, `hyprpm reload` loads nothing. `hyprpm add` also refuses to run until that record matches.

## The forks

### `lukastk/hyprgrass` (touchscreen gestures, pocket4 only)

Three changes, in two places:

1. **Manifest** (on `main`): removes the `[hyprgrass-pulse]` and `[hyprgrass-backlight]` tables from `hyprpm.toml`. Upstream deleted both examples' source (horriblename/hyprgrass e8f09840, 2026-08-31) but kept their manifest entries, whose build steps only echo a deprecation notice. After the aquamarine 0.15 ABI change this left pocket4 with no plugins loaded at all, so no touch gestures.
2. **Touch-down refocus fix** (branch `pocket4-hyprland-0.56.2`, commit `fa86801`). `GestureManager::onTouchDown` called `refocus()` with no position, which sent `wl_pointer.motion` to the app right before every `wl_touch.down`. Chromium (Brave, Obsidian) hides its touch-selection handles and touch menu on pointer motion, so no selection handle could be dragged and the Cut/Copy bar could not be tapped. It now calls `refocus(touchPos)`, like Hyprland's own touch-down.
3. **`pointer_emulation_mods`** (same branch, commit `9ff50a2`). While the named modifiers are held, a finger drives the mouse (press, drag, release), so Shift + finger drag selects text. Set in `src/hyprland/60-gestures.lua.jinja`.

`main`'s `hyprpm.toml` pins Hyprland 0.56.2 (`efb50993…`) to the branch tip `9ff50a2` instead of upstream's `8e605468`, which the branch is based on.

- **On a Hyprland update:** upstream's pin for the new Hyprland commit builds WITHOUT changes 2 and 3. Rebase the branch onto that pin (name it after the new version), move the new pin to its tip, and rerun the installer. Missed, it fails loudly: Hyprland reports `pointer_emulation_mods` as an unknown option in `hyprctl configerrors`.
- **Drop when:** all three are upstream, or the Shift drag is no longer wanted and the first two are. Checks:
  - manifest: `gh api repos/horriblename/hyprgrass/contents/hyprpm.toml --jq .content | base64 -d | grep -c '^\[hyprgrass-'` prints `0`;
  - refocus: `gh api repos/horriblename/hyprgrass/contents/src/GestureManager.cpp --jq .content | base64 -d | grep -c 'g_pInputManager->refocus();'` prints `0`;
  - pointer emulation: an equivalent option exists upstream (none at the time of writing; nothing has been proposed upstream yet).
- **Related:** range-handle dragging also needs the Hyprland patch in `packages/hyprland/` (see its README): with only this fork, grabbing a handle still ends the drag.

### `lukastk/hyprexpo` (workspace overview, both profiles)

- **Change:** moves the Hyprland 0.56.2 pin (`efb50993…`) from `5891014` to `c620890`, which contains sandwichfarm/hyprexpo#137.
- **Why:** #137 makes a tap in the grid overview select the workspace under the finger, not the one under the stale mouse cursor. Without it, a touch-only Pocket cannot pick a workspace after the three-finger-up swipe. The published 0.56.2 pin predates the fix, and upstream moves pins only through a maintainer's release promotion (`docs/guides/release-promotion.md` in that repository).
- **Drop when:** upstream's pin for the running Hyprland commit is a descendant of #137's merge (`c7493432`). Check with `gh api repos/sandwichfarm/hyprexpo/compare/c7493432...<pinned commit> --jq .status`; `ahead` or `identical` means drop. On a newer Hyprland, look up that commit's pin first.

## Keeping the forks current

A fork that misses upstream's newest pin builds the wrong source after the next Hyprland update. `.github/workflows/sync-plugin-forks.yml` calls GitHub's `merge-upstream` for each fork daily (and on manual dispatch). Fast-forwards and clean merges go through. A conflict fails the job, and usually means upstream changed the same manifest line as the fork, which is exactly when to re-check the drop condition.

The workflow needs the repository secret `PLUGIN_FORK_SYNC_TOKEN`, a token that can write to both forks, including their `.github/workflows` (upstream edits its own workflows, which the built-in `GITHUB_TOKEN` can never write). It is currently a copy of the account-wide `GITHUB_TOKEN` from 1Password, set without printing it via `secret get GITHUB_TOKEN | gh secret set PLUGIN_FORK_SYNC_TOKEN -R lukastk/myarch` (2026-09-17). That was a deliberate trade-off: no extra token to manage, against a secret in a public repository that can administer the whole account. Pull requests from other people's forks never receive secrets, and the job runs no third-party actions. To narrow it, replace the secret with a fine-grained token limited to `lukastk/hyprexpo` and `lukastk/hyprgrass`, with **Contents** and **Workflows** read/write. **Rotating `GITHUB_TOKEN` in 1Password does not update this copy.** Re-run the command above, or the job fails every day until you do.

GitHub Actions is **disabled on both forks**. Enabled, every sync would run upstream's own CI in the fork (hyprexpo's site deploy fails there for lack of secrets). Pull requests to upstream run their checks in the upstream repository, so the forks lose nothing.

## Switching a plugin back to upstream

1. In `install.py`, point the plugin URL back at upstream and delete its `TODO(cleanup)` line.
2. Delete the fork's entry in `.github/workflows/sync-plugin-forks.yml`, and the whole workflow once no forks remain.
3. Delete the fork's section here, and this file once no forks remain. Update the assertion in `test_every_plugin_fork_is_synced_from_upstream` in `tests/test_render.py`.
4. Rerun the installer. `configure_plugins` sees the installed repository's author differ from the declared URL's, then removes it, updates, and re-adds from upstream.
5. Archive the fork on GitHub.
