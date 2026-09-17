# Patched Hyprland for pocket4 touch selection

Arch's `hyprland` 0.56.2-3 with one patch, `touch-synthetic-pointer.patch`, built
as `0.56.2-3.1`. pocket4 lists it in `profiles/pocket4.toml` `[packages] patched`, so
`install.sh` builds and installs it (`packages/install-patched hyprland`); ideapad
keeps the stock package.

<!-- TODO(cleanup): delete packages/hyprland and the "hyprland" entry in profiles/pocket4.toml [packages] patched, then reinstall the stock Arch hyprland — once Hyprland stops sending synthetic pointer motion while touch is the last input; see packages/hyprland/README.md. -->

## What the patch fixes

`CInputManager::simulateMouseMovement()` re-sends the pointer position whenever a
surface maps, unmaps or moves under it. While touch is the last input, nobody is
using the pointer, but clients still receive `wl_pointer.enter`/`motion`, and
Chromium (Brave, Obsidian) takes that as mouse activity and hides its
touch-selection handles and touch menu. Grabbing a selection handle closes
Chromium's Cut/Copy bar, which unmaps a subsurface, which fires exactly that
motion, so every range-handle drag ended the moment it started. The patch returns
early while `m_lastInputTouch` is set and no drag target is held (touch-driven
mouse-bind drags from hyprgrass still need the move).

The other half of the problem, hyprgrass sending pointer motion on every touch
down, is fixed in the `lukastk/hyprgrass` fork (`docs/plugin-forks.md`).

Measured on pocket4, 2026-09-17, with a uinput touchscreen: with Brave under
`WAYLAND_DEBUG=1`, a touch on the handle was followed by `wl_subsurface.destroy`
and then `wl_pointer.enter` + `wl_pointer.motion`, and the handles vanished. With
the patch the right handle drags the selection word by word in Brave and in
Obsidian, and the bar's Copy button works by touch.

## Build and install

`install.sh --profile pocket4` does it: `packages/install-patched hyprland` copies
this directory to `~/.cache/myarch/packages/hyprland`, runs
`makepkg --syncdeps --cleanbuild --clean` (the build tree, ~3 GB, is removed afterwards), and `pacman -U`s the `hyprland` package (not
`hyprpm` or `-debug`). It skips the build when `0.56.2-3.1` is already installed, so
**bump the suffix (3.1 -> 3.2) whenever the patch changes.** Restart Hyprland for a
new build to take effect.

## When Arch updates Hyprland

A system upgrade (`pacman -Syu`) replaces this build with Arch's newer one, and
handle drags break again. The next `install.sh` run then stops, because
install-patched refuses to build 0.56.2 once the repositories carry anything but
0.56.2-3. To fix it:

1. Check whether upstream already has an equivalent guard in
   `CInputManager::simulateMouseMovement`. If so, delete this directory and the
   `"hyprland"` entry in `profiles/pocket4.toml`.
2. Otherwise take Arch's new PKGBUILD
   (`https://gitlab.archlinux.org/archlinux/packaging/packages/hyprland`), re-apply
   the three edits here (pkgrel suffix, the patch in `source`/`sha256sums`, `patch`
   in `prepare()`), rebase the patch onto the new source, and rerun `install.sh`.
3. The hyprgrass fork needs its matching update too (`docs/plugin-forks.md`).
