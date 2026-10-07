# myarch — active traps and follow-ups

Detailed measurements, rationale, failed experiments, recovery procedures, and
original dated entries: [desktop investigation topic index](docs/desktop-investigations.md#topic-index).
Read only the relevant section. These notes summarize findings through 2026-10-07;
verify live versions/state rather than reusing historical IDs or `/tmp` probes.

- **Pocket pad:** a firmware-relative mouse, not a Linux touchpad.
  `input:touchpad:*` affects IdeaPad only; keep Pocket `natural_scroll=false`.
  Stock acceleration won the timing comparison; do not repeat custom-curve
  tuning without new evidence. Use `hyprctl eval`, not unsupported `keyword`,
  with the Lua config.
- **Fuzzel:** `keyboard-focus=on-demand` permits touch dismissal via a window
  or bar, not bare desktop. Test real clicks, not `dispatch focuswindow`.
  Namespace is `launcher`; width is characters; `;` comments break its config.
- **Plugins/touch:** ABI includes library versions, not just the compositor
  commit. Every plugin must build before hyprpm records the new hash.
  Check the actual pinned build, not just upstream HEAD. Hyprgrass's NODELETE
  symbols mean unload does not remove its listeners: rebuilt code needs a
  coordinated compositor restart, not a misleading “all plugins unloaded” test.
- **Lock fix verified 2026-09-28:** patched Hyprland 0.56.2-3.2 (`37d3bfd`)
  preserves synthetic pointer motion while locked; suppress it only for
  touch-last + no drag target + **unlocked**. Touch-last typing and Brave/Obsidian
  selection-handle drags passed real-hardware checks. Do not regress either.
  Post-3.2 DPMS comparison remains pending; the separate blocking three-second
  power hook was unchanged. This does not diagnose every historical wake stall.
- **Audio:** Ear (a) pairing and fragmentary HFP dictation findings are in the
  archive; built-in mic via Super+Ctrl+I is the verified workaround.
  Super+Ctrl+O uses WirePlumber's persistent output preference, not a new daemon.
  Automatic clears output only: `wpctl clear-default 0` uses the Audio/Sink
  settings ID; omitting `0` also clears microphone/camera preferences.

Desktop restart, debugger, password, suspend, and hands-on test safety remain
mandatory in [AGENTS.md](AGENTS.md#desktoptest-safety).
