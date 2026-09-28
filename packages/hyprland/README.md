# Patched Hyprland for pocket4 touch selection

Arch's `hyprland` 0.56.2-3 with one patch, `touch-synthetic-pointer.patch`, built
as `0.56.2-3.2`. pocket4 lists it in `profiles/pocket4.toml` `[packages] patched`, so
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
early while `m_lastInputTouch` is set, no drag target is held, and the session is
**not locked** (touch-driven mouse-bind drags and lock-screen focus still need
the move).

The other half of the problem, hyprgrass sending pointer motion on every touch
down, is fixed in the `lukastk/hyprgrass` fork (`docs/plugin-forks.md`).

Measured on pocket4, 2026-09-17, with a uinput touchscreen: with Brave under
`WAYLAND_DEBUG=1`, a touch on the handle was followed by `wl_subsurface.destroy`
and then `wl_pointer.enter` + `wl_pointer.motion`, and the handles vanished. With
the patch the right handle drags the selection word by word in Brave and in
Obsidian, and the bar's Copy button works by touch.

## Lock-screen focus regression fixed in 3.2

The original 3.1 guard also suppressed the synthetic movement used by
`SSessionLockSurface`'s map/commit handlers to acquire keyboard focus. On
2026-09-28, locking immediately after touchscreen input reproduced a mapped lock
surface with **null keyboard focus** for over 20 seconds; typing produced no
dots. Moving the trackpad **without clicking** restored focus to that same lock
surface and typing immediately worked. The pointer-last comparison worked.
No suspend or DPMS was needed to reproduce the touch-last failure.

3.2 exempts locked sessions from the guard. Hyprland's locked-input path focuses
the lock surface rather than the underlying application, so the exception does
not remove the touch-selection protection on an unlocked desktop. Both the
touch-driven drag exception and ordinary mouse behavior remain unchanged.

Verified on pocket4 after installing 3.2 and restarting, 2026-09-28 13:42: touch
remained the last input, but keyboard and pointer focus matched the mapped lock
surface at the first probe (~0.5 seconds). Lukas confirmed typing worked without
moving the trackpad, and the journal recorded successful authentication/unlock.
This verifies the reproduced touch-last focus failure, not every historical
wake delay. The separate three-second blocking power-restoration hook is unchanged.

After a rebuild, test touch-last lock, pointer-last lock, lock + DPMS, and
touch-selection handle dragging in Brave/Obsidian. Post-3.2 DPMS and real
selection-handle checks are still pending. Never log password keycodes to
diagnose focus.

## Build and install

`install.sh --profile pocket4` does it: `packages/install-patched hyprland` copies
this directory to `~/.cache/myarch/packages/hyprland`, runs
`makepkg --syncdeps --cleanbuild --clean` (the build tree, ~3 GB, is removed afterwards), and `pacman -U`s the `hyprland` package (not
`hyprpm` or `-debug`). It skips the build when `0.56.2-3.2` is already installed, so
**bump the suffix (e.g. 3.2 -> 3.3) whenever the patch changes.** Rebuild the
hyprpm plugins after the compositor update (`hyprpm update -f`), and restart
Hyprland for the new compositor and plugin builds to take effect. Coordinate
that restart: it closes the running desktop apps. The 3.2 change keeps the same
upstream commit and library ABI; no plugin pin rebase is needed.

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
