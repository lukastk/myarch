# Patched Hyprland for pocket4 touch selection

Arch's `hyprland` 0.56.2-3 with one patch, `touch-synthetic-pointer.patch`, built
as `0.56.2-3.1`. It is installed on pocket4 only, and by hand: `install.sh`
does not build it.

<!-- TODO(cleanup): delete packages/hyprland (and reinstall the stock Arch hyprland) — once Hyprland stops sending synthetic pointer motion while touch is the last input; see packages/hyprland/README.md. -->

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

```bash
cd packages/hyprland
makepkg -f                      # needs base-devel and the PKGBUILD's makedepends
sudo pacman -U hyprland-0.56.2-3.1-x86_64.pkg.tar.zst
```

Restarting Hyprland is required for it to take effect. Build output
(`src/`, `pkg/`, `*.pkg.tar.zst`, the source tarball) is ignored by git.

## It is lost silently

The next Arch upgrade of `hyprland` (anything newer than 0.56.2-3.1) replaces it,
and handle drags break again with no error. Before accepting that upgrade, rebase
the patch onto the new source and rebuild, or check whether upstream has fixed
it: search Hyprland's `simulateMouseMovement` for a touch-input guard.
