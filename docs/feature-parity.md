# Feature parity contract

A myarch change is incomplete if it regresses any item below.

| Area | Invariant |
|---|---|
| Sesh/SST | `sst`, cockpit, tickets, tmux keyboard/mouse/clipboard, cross-machine sessions |
| Workspaces | 1–15 banks, role mapping, persistent slots, chooser, app pins, scratchpad, `hypr-load-main` |
| Overview | Super+G and three-finger-up open Hyprexpo with real workspace IDs |
| IdeaPad gestures | Native three-finger horizontal workspace movement and up overview |
| Pocket gestures | Hyprgrass three-finger horizontal/up and four-finger OSK |
| Pocket display/touch | Rotation always changes panel and touchscreen together; orientation, flip, and scale remain explicit |
| Pocket tablet mode | Manual 1.6↔2.0 toggle; exiting hides OSK; no fabricated auto-detection |
| Pocket OSK | Running equals visible; CLI/bar/gesture toggle; portrait and landscape dimensions |
| Pocket thermals | quiet/chill/balanced/performance coordinate power limits and fan curve through `pocket4-mode` |
| Pocket bar | Correct one/two-row layout and hit mapping at logical widths 1600/1280/1000/800 |
| Dictation | Hold/latch, cleanup promotion, cancel, touch finish/start, local backend, Pocket mic correction |
| Terminal | Foot touch-to-TUI on Pocket; Kitty keyboard protocol through tmux; Obsidian URLs |
| Displays | extend/external/internal/mirror, mirror overlay restore, workspace restoration, external-only gaming |
| Brightness | Hardware backlight then gamma, monotonic and reversible |
| Idle/suspend | hypridle, redbull, bar inhibitor, and server mode retain distinct lock/blank/suspend semantics |
| Wallpaper | Rotation, next, picker/live preview, pin, and independent theme selection |
| Notifications | Sesh, timer, dictation, and setup failures remain visible |
| Clipboard/capture | Text/image history, Sesh relay, screenshots, sensitive QR output |
| Session environment | SSH/Sesh panes recover the live Wayland/DBus/Hyprland environment |
| Key layer | keyd Caps→F12 and language switching remain available |
| Fonts | Nerd symbols and JP/KR/SC/TC/HK Noto selection remain correct |
| Web apps | ChatGPT, Claude, and WhatsApp classes/workspace pins remain stable |

## Required static validation

- `./scripts/test`
- no Hyprland config errors
- no secrets or private screenshot/research artefacts
- both profiles and every theme render
- Waybar JSONC parses
- Python compiles and ShellCheck passes
- installation reruns idempotently

## Deployment policy

Pocket 4 was validated first; IdeaPad was deployed only after the separate explicit greenlight on 2026-08-21. Future profile deployments remain explicit rather than inferred from hardware.