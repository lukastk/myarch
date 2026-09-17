# Hyprpm plugin forks

myarch installs both hyprpm plugins from forks under `lukastk`, each one commit on top of upstream. They are temporary: every fork has a concrete drop condition below, and every site to change carries the same `TODO(cleanup):` text (`grep -rn "TODO(cleanup): drop the lukastk/"`).

## Why a manifest change needs a fork

Two hyprpm behaviours (read from the v0.56.2 source, `hyprpm/src/core/PluginManager.cpp`) decide everything here:

- **hyprpm builds the pinned commit, not HEAD.** It reads the plugin list from the repository's HEAD `hyprpm.toml`, then resets the checkout to the `commit_pins` entry for the running Hyprland commit and builds that. A fix merged upstream reaches hyprpm users only once a pin points at it.
- **After an ABI change, one failed build blocks every plugin.** The ABI string includes library versions (`..._aq_0.15_hu_0.14_...`), so an aquamarine or hyprutils update changes it without a new Hyprland commit. `hyprpm update` then records the new ABI only if every plugin in every repository builds; until it does, `hyprpm reload` loads nothing. `hyprpm add` also refuses to run until that record matches.

## The forks

### `lukastk/hyprgrass` (touchscreen gestures, pocket4 only)

- **Change:** removes the `[hyprgrass-pulse]` and `[hyprgrass-backlight]` tables from `hyprpm.toml`.
- **Why:** upstream deleted both examples' source (horriblename/hyprgrass e8f09840, 2026-08-31) but kept their manifest entries, whose build steps only echo a deprecation notice. After the aquamarine 0.15 ABI change this left pocket4 with no plugins loaded at all, so no touch gestures.
- **Drop when:** upstream's `hyprpm.toml` no longer lists either table. Check with `gh api repos/horriblename/hyprgrass/contents/hyprpm.toml --jq .content | base64 -d | grep -c '^\[hyprgrass-'`; `0` means drop.

### `lukastk/hyprexpo` (workspace overview, both profiles)

- **Change:** moves the Hyprland 0.56.2 pin (`efb50993…`) from `5891014` to `c620890`, which contains sandwichfarm/hyprexpo#137.
- **Why:** #137 makes a tap in the grid overview select the workspace under the finger, not the one under the stale mouse cursor. Without it, a touch-only Pocket cannot pick a workspace after the three-finger-up swipe. The published 0.56.2 pin predates the fix, and upstream moves pins only through a maintainer's release promotion (`docs/guides/release-promotion.md` in that repository).
- **Drop when:** upstream's pin for the running Hyprland commit is a descendant of #137's merge (`c7493432`). Check with `gh api repos/sandwichfarm/hyprexpo/compare/c7493432...<pinned commit> --jq .status`; `ahead` or `identical` means drop. On a newer Hyprland, look up that commit's pin first.

## Keeping the forks current

A fork that misses upstream's newest pin builds the wrong source after the next Hyprland update. `.github/workflows/sync-plugin-forks.yml` calls GitHub's `merge-upstream` for each fork daily (and on manual dispatch). Fast-forwards and clean merges go through. A conflict fails the job, and usually means upstream changed the same manifest line as the fork, which is exactly when to re-check the drop condition.

The workflow needs the repository secret `PLUGIN_FORK_SYNC_TOKEN`: a fine-grained personal access token with resource owner `lukastk`, repository access limited to `lukastk/hyprexpo` and `lukastk/hyprgrass`, and **Contents** and **Workflows** read/write. Workflows is required because upstream edits its own `.github/workflows`, which the built-in `GITHUB_TOKEN` can never write. Set it with `gh secret set PLUGIN_FORK_SYNC_TOKEN -R lukastk/myarch`. Once the token expires, the job fails every day until it is replaced.

GitHub Actions is **disabled on both forks**. Enabled, every sync would run upstream's own CI in the fork (hyprexpo's site deploy fails there for lack of secrets). Pull requests to upstream run their checks in the upstream repository, so the forks lose nothing.

## Switching a plugin back to upstream

1. In `install.py`, point the plugin URL back at upstream and delete its `TODO(cleanup)` line.
2. Delete the fork's entry in `.github/workflows/sync-plugin-forks.yml`, and the whole workflow once no forks remain.
3. Delete the fork's section here, and this file once no forks remain. Update the assertion in `test_every_plugin_fork_is_synced_from_upstream` in `tests/test_render.py`.
4. Rerun the installer. `configure_plugins` sees the installed repository's author differ from the declared URL's, then removes it, updates, and re-adds from upstream.
5. Archive the fork on GitHub.
