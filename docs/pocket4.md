# Pocket 4 integration

The GPD Pocket 4 panel is physically portrait (`1600×2560`) and mounted sideways. Desktop landscape is Hyprland transform 3. The touchscreen must always receive the same transform or taps land in the wrong place.

## Display states

| State | Physical | Scale | Transform | Logical | Bar |
|---|---:|---:|---:|---:|---|
| Landscape desktop | 2560×1600 | 1.6 | 3 | 1600×1000 | one row, normal metrics |
| Landscape tablet | 2560×1600 | 2.0 | 3 | 1280×800 | two rows, normal metrics |
| Portrait desktop | 1600×2560 | 1.6 | 0 | 1000×1600 | two rows, normal metrics |
| Portrait tablet | 1600×2560 | 2.0 | 0 | 800×1280 | two rows, compact metrics |

`pocket4-waybar` derives the layout from logical width, not orientation alone. A row whose minimum width exceeds its layer surface is a correctness failure: Hyprland scales the oversized buffer and visible touch targets no longer correspond to actual hit regions.

## Hardware authorities

- `pocket4-display` — orientation, flip, scale; changes monitor and touchscreen transforms together.
- `pocket4-tablet-mode` — explicit 1.6/2.0 state; there is no reliable physical tablet-mode sensor.
- `pocket4-osk` — spawn-to-show / kill-to-hide `wvkbd-deskintl`; running equals visible.
- `pocket4-thermal-mode` — delegates to `pocket4-mode`; quiet/chill/balanced/performance set both CPU envelope and fan curve.
- `pocket4-ws` / watcher — Lua-compatible workspace dispatch and event-driven bar refresh.
- Hyprgrass — touchscreen gestures inside the compositor; no direct evdev ACL/daemon.

The Pocket's keyboard fold does not change `SW_LID`, and the screen accelerometer cannot distinguish upright tablet use from an open laptop. Automatic tablet detection would invent state and is deliberately absent.

## Real-device validation

For any Pocket UI/display change:

1. Save the initial orientation/tablet state.
2. Visit all four table states.
3. At each state inspect the rendered bar, query Waybar layer dimensions, and confirm no surface exceeds logical width.
4. Tap the left edge, centre workspaces/dictation, each Pocket hardware control, and right edge/tray. Confirm the activated command matches the visible target.
5. Touch all four panel corners after rotation.
6. Test three-finger horizontal/up and four-finger-up.
7. Toggle OSK by bar, CLI, and gesture; verify dimensions in both orientations.
8. Cycle thermal modes and compare bar state with `pocket4-mode status`.
9. Test dictation hold, latch, cleanup, cancel, and touch finish.
10. Restore landscape desktop state.

The compact 800-logical-pixel metrics remain physically touch-safe because scale 2.0 turns their smaller logical dimensions into equal-or-larger glass dimensions than normal metrics at scale 1.6.