# myarch — local notes

## Pocket 4 trackpad: measured facts, and a tuning experiment that FAILED

Measured on-device 2026-09-14. Recorded so nobody re-derives it — most of these
contradict what the hardware descriptors imply.

### The hardware

- The pad is **not a touchpad to Linux**. Its HID report descriptor
  (`/sys/kernel/debug/hid/0003:258A:000C.0002/rdesc`) declares one Generic
  Desktop/Mouse collection — 8-bit RELATIVE X/Y/Wheel/AC-Pan, five buttons —
  and **no Digitizer usage page at all** (`EV=17`, no `EV_ABS`, `PROP=0`).
  Multitouch is resolved in firmware and delivered as finished mouse events, so
  gestures/pinch/palm-rejection/pixel-precise scroll are *unreachable*, not
  merely unconfigured. The same descriptor goes to Windows.
- **125 Hz, not the 100 Hz the descriptor implies.** Median frame gap is 8.00 ms:
  host controllers round the descriptor's `bInterval 10` down to the nearest
  power of two. So `usbhid.mousepoll` has nothing to recover — don't try it.
- **~750 counts across the pad, ~530 top-to-bottom** (≈250–300 DPI — coarse).
  Screen is 1600x1000 logical (2560x1600 at scale 1.6, transform 3).
- **Scroll has no sub-notch resolution.** `REL_WHEEL` is only ever ±1 and
  `WHEEL_HI_RES` only ever ±120 — the 120s are the kernel synthesising hi-res
  from whole notches. Velocity is encoded purely as notch *rate*. The "pulsing"
  scroll is structural; no compositor setting can smooth it.
- **`natural_scroll` must stay false.** The firmware already emits wheel deltas
  in the natural direction — fingers moving DOWN send `REL_WHEEL +1` (measured
  136 of 144 events). Setting it true INVERTS scrolling that is correct.
- **keyd does not grab the pad.** It holds `event4` open (`[ids] *`) but passes
  events through; all input arrives on `event4`, none on the keyd virtual
  pointer. Per-device config must target `hailuck-co.-ltd-usb-keyboard-mouse`.

### Gotchas

- **`hyprctl keyword` is INERT against this config.** The Lua parser rejects it
  ("keyword can't work with non-legacy parsers. Use eval."). It fails *quietly*
  enough to invalidate a whole measurement run. Use:
  `hyprctl eval 'hl.config({input={...}})'` / `hl.device({...})`.
- Hyprland picks `input:touchpad:*` vs `input:*` per device via
  `ISTOUCHPAD = pointer capability && libinput_device_get_size() == 0`
  (InputManager.cpp). The Pocket pad reports no size, so **everything under
  `input:touchpad:` is inert on pocket4** — it reaches ideapad only.
- A uinput device duplicating an existing evdev name gets suffixed by Hyprland
  (`...-mouse-1`), so it will NOT pick up the original's `device` block.

### The failed experiment — do not repeat without new evidence

Stock libinput `adaptive` gives gain 1.00 below ~0.4 counts/ms, then **caps hard
at 2.00**. That cap means a maximum-speed full-width flick covers 750 x 2.0 =
1500 px of a 1600 px screen, so crossing the display in one sweep is
arithmetically impossible. That looked like the cause of "it's worse than the
MacBook". **It was not.**

A 13-point custom curve (0.85 at the slow end for precision, rising to 5.87 at
5 counts/ms for reach) was built and verified — gain is exactly `f(x)/x` logical
px per count, confirmed by injecting known counts through uinput and reading
`hyprctl cursorpos`; `f(x)=x` measures exactly 1.000 px/count.

Benchmarked on aimtest.org, 30 targets:

| condition       | accuracy | avg time | hit   |
|-----------------|----------|----------|-------|
| MacBook         | 90%      | 817 ms   | 27/30 |
| pocket4 stock   | 90%      | 1035 ms  | 27/30 |
| pocket4 tuned   | 97%      | 1189 ms  | 29/30 |

The curve bought accuracy and **lost 154 ms per target** — and stock ran first,
so the practice effect favoured the tuned run and it still lost. Reverted
2026-09-14; Lukas prefers stock.

**What this says:** the Mac gap lives in target *acquisition*, not traversal, and
raising top-end gain makes acquisition worse (the ballistic phase overshoots and
you repay it in corrections). Note Mac vs pocket4-stock: identical accuracy,
identical hits, 218 ms apart, **both on their own stock settings** — so ~21% of
the gap is not a curve problem at all. It is most likely the hardware: ~250-300
DPI on a small surface against Apple's much finer digitizer. That part is not
tunable.

If this is ever revisited, the only curve worth trying is one that **never goes
below stock's gain at the low end** and diverges from stock *only* above
~1.5 counts/ms, where stock flatlines. And on aimtest.org, judge it on **average
time at equal-or-better accuracy** — the site's "Score" is just
`targets hit x 133.4` and says nothing about speed.

## Launcher: wofi → fuzzel, and the input deadzone that drove it

Measured on-device 2026-09-15. Recorded so the numbers aren't re-derived.

### The complaint and the actual cause

"Super+R then Enter immediately" lost the Enter. Two separate things were
suspected; only one was real.

- **The `layersIn` fade was NOT the cause.** A layer surface is mapped *and
  already holds keyboard focus* while it fades, so the animation never eats a
  keystroke. It was set to speed 4 (400ms) from the ML4W-ish preset the whole
  animation block came from, which meant the launcher was fully interactive
  ~300ms before it finished appearing — lag that looked real but wasn't.
- **The real cause was an input deadzone**: the gap between the keypress and
  the moment the launcher's surface accepts input. Anything inside it goes to
  the previously focused window, silently.

### Method

Spawn the launcher, inject one key with `wtype` after a fixed delay, check
whether it registered (dmenu: did the selection come out; drun: did Escape
close it). 5 trials per delay. Scripts are throwaway; the method is the point.

### Numbers — first delay that lands 5/5

| path | wofi | fuzzel |
|---|---|---|
| dmenu picker | 125 ms | 20 ms |
| drun / app launcher (Super+Alt+Space) | 100 ms | 30 ms |
| `myarch menu` (Super+R), end to end | 175 ms | 100 ms |

Breakdown of a launch: ~60ms for wofi to map its layer (fuzzel: ~15ms), ~40ms
more before input is accepted, and for Super+R a further ~35ms of Python
interpreter start (measured: 31–39ms for `myarch`'s import set) before fuzzel
is even spawned. **That Python hop is now the largest remaining term on
Super+R** — it is why Super+R sits at 100ms while Super+Alt+Space is at 30ms.

The deadzone can never reach zero: a key pressed before the surface exists has
nowhere to go. The goal is only to get it under the time it takes to press a
second key.

### fuzzel facts worth not re-deriving

- **Its ini parser rejects `;` comments** with a hard syntax error that fails
  the whole config. `install.py`'s `comment_prefix()` special-cases the fuzzel
  directory for this, as it already did for foot. `fuzzel --check-config`
  catches it; CI can't (no fuzzel binary), so `test_render.py` asserts the
  prefix instead.
- **No dmenu cache unless you ask for one.** wofi needed `--cache-file
  /dev/null` at every call site to stop frecency reordering the list; fuzzel
  only caches dmenu entries if `--cache` is passed, so the guard was dropped,
  not translated. Verified: unfiltered input order is preserved, and
  `--no-sort` changed nothing on the real workspace/cliphist lists.
- **Case-insensitive by default** both directions, so `--insensitive` had no
  translation either.
- **Layer-shell namespace is `launcher`**, not `fuzzel` — that is what a
  layerrule or screencast exclusion must match, and what to grep for in
  `hyprctl layers`.
- **Single-instance lock** (`$XDG_RUNTIME_DIR/fuzzel-$WAYLAND_DISPLAY.lock`).
  The `myarch menu` → " Applications" double hop is safe because `select()`
  blocks on the first instance's exit; measured, the second opens 11ms later.
- **Colours are 8-digit RGBA with no leading `#`** (hence `{{ theme.x[1:] }}ff`).
- `width` is in CHARACTERS. 72 is chosen to fit pocket4's narrowest logical
  width (800, portrait at scale 2.0). The keybinding catalogue's two longest
  lines (90 and 84 chars) truncate rather than overflow the screen.

### Not tried

A Hyprland `layerrule` can scope an animation *style* to one namespace but not
a *speed*, so `layersIn` at 1.2 (120ms) is necessarily global — it also speeds
up mako and waybar. `animation none` scoped to `launcher` is the only way to
single out the launcher, and it was not wanted.

### Touch dismissal: `keyboard-focus=on-demand`

fuzzel's default `exclusive` **locks** keyboard focus to itself until it closes,
so nothing outside can ever take focus and `exit-on-keyboard-focus-loss` (which
defaults to yes) never fires. On a touch-only Pocket that meant a launcher
opened by touch could not be closed by touch at all. `on-demand` fixes it.

Measured on pocket4 2026-09-15 with a uinput virtual pointer (raw ioctls; note
the legacy `uinput_user_dev` struct is **written** to the fd, not sent as an
ioctl — getting that wrong is a `ValueError: ioctl argument 3 is too long`):

| tap target | exclusive | on-demand |
|---|---|---|
| a window | stays open | **dismisses** |
| the bar (waybar) | stays open | **dismisses** |
| bare desktop | stays open | stays open |

The bar result is what makes this good enough: waybar spans the full width at
the top of every workspace, so there is always a dismiss target. Bare desktop
never dismisses because no surface there takes keyboard focus.

**`hyprctl dispatch focuswindow` is NOT a valid proxy for a click here** — it
does not move keyboard focus off an on-demand layer surface, so an early test
using it wrongly concluded on-demand did not work. Only a real pointer click
does. Use uinput.

**The follow_mouse hazard does not apply.** `input:follow_mouse = 1` is set
(`50-input.lua.jinja`), which is exactly the Sway <= 1.7 case fuzzel's man page
warns about, but Hyprland only refocuses off the layer surface on a real click:
0 spurious closes over 26 motion trials (gentle drift, fast corner-to-corner
flicks, and motion immediately after a window had been clicked). One close was
seen in a single early run and never reproduced — if the launcher ever vanishes
on its own, that is the loose end.

**It costs a little latency.** Keys land reliably from ~50ms instead of ~20ms
(at 20ms: exclusive 8/8, on-demand 6/8). Still far inside a two-key interval and
far better than wofi's 125ms, so the trade is worth it.

## hyprpm: why touch gestures silently vanished, and the hyprgrass fork

Diagnosed on pocket4 2026-09-15/17 from hyprpm's v0.56.2 source
(`hyprpm/src/core/PluginManager.cpp`, `main.cpp`). Symptom: `hyprctl plugin
list` says `no plugins loaded`; `hyprpm reload` says `headers are not
up-to-date` even right after `hyprpm update` claims `Headers up to date`.

- **All-or-nothing after an ABI change.** The ABI string includes library
  versions (`..._aq_0.15_hu_0.14_...`), so an aquamarine/hyprutils bump changes
  it with no Hyprland commit change. After that, `hyprpm update` only records
  the new hash if EVERY plugin in EVERY repo builds; otherwise `reload` loads
  nothing. The state file is `/var/cache/hyprpm/<user>/state.toml` (`hash`).
- **The failing plugins were hyprgrass's own dead stubs.** Upstream deleted
  `hyprgrass-pulse`/`hyprgrass-backlight` source (e8f09840, 2026-08-31) but kept
  their `hyprpm.toml` entries with `echo ... deprecated` build steps, which
  never produce a `.so`.
- **Fix: `lukastk/hyprgrass`**, upstream + one commit dropping those two
  entries. It works because hyprpm reads the plugin list from the repo's HEAD
  manifest *before* resetting to the commit pin, then builds the pinned
  upstream source. Consequence: the fork's HEAD must contain upstream's pin
  for the running Hyprland, or hyprpm builds the fork's unpinned HEAD instead.
- **Second fork, `lukastk/hyprexpo` (2026-09-17)**: the "can't tap a workspace
  after three-finger-up" bug came back because hyprpm builds the PINNED commit,
  and the 0.56.2 pin predates Lukas's own fix (sandwichfarm/hyprexpo#137). The
  fork moves only that pin. A hyprexpo that "has the fix on master" is not
  enough — check what the pin points at (`hyprctl plugin list` shows
  `dev+<sha>` of the build actually loaded).
- Both forks are kept current by `.github/workflows/sync-plugin-forks.yml`
  (needs the `PLUGIN_FORK_SYNC_TOKEN` secret). Actions are DISABLED on the forks
  on purpose: enabled, each sync runs upstream's CI there (hyprexpo's site
  deploy fails without secrets). Drop conditions and switch-back steps:
  `docs/plugin-forks.md`. Keep-vs-drop decision pad in myvault:
  `pad/Revisit myarch's hyprpm plugin forks.md`.
- `hyprpm add` requires the ABI hash to already match, so a broken repo must
  be `remove`d before `update`, and only then can a replacement be `add`ed.
  `install.py configure_plugins` does exactly that when an installed repo's
  author differs from the declared URL's.
- With a stale hash, `hyprpm remove` cannot unload the plugin (it silently
  skips). A plugin loaded by hand with `hyprctl plugin load` survives, and
  `enable` will not reload a plugin name that is already loaded.
- Stopgap without any of this: `hyprctl plugin load
  /var/cache/hyprpm/<user>/<repo>/<plugin>.so` — only safe when those `.so`s
  were just built for the running Hyprland.

## NEVER interrupt a gdb attached to the live compositor (crashed the session 2026-09-17)

`sudo gdb -batch` attached to the running Hyprland, stopped with `pkill -INT gdb`:
the SIGINT stops the inferior with the signal PENDING, and `detach` then delivers
it to Hyprland, which exits. start-hyprland restarts it with `--safe-mode`, every
app window is gone, and the new instance has a NEW HYPRLAND_INSTANCE_SIGNATURE
(existing shells still point at the dead one: "Couldn't connect to .socket.sock").

To trace compositor internals, load a throwaway plugin that hooks the function
(`HyprlandAPI::createFunctionHook`) and logs `backtrace()` to a file — plugins
load and unload live with `hyprctl plugin load|unload`, no ptrace involved.

Recovering from safe mode without logging out (GDM has no autologin): point
HYPRLAND_INSTANCE_SIGNATURE at the newest dir in /run/user/1000/hypr/, then
`hyprctl eval 'hl.dispatch(hl.dsp.cursor.move({ x = X, y = Y }))'` onto the safe-mode
dialog's "Load config" button and click with a uinput mouse (a uinput touch tap does
NOT press hyprland-dialog buttons). Loading the config does not fire
`hyprland.start`, so re-run every `hl.exec_cmd` in `20-autostart.lua.jinja` by hand
(`hyprctl eval 'hl.exec_cmd("...")'`) and kill the stale pocket4-ws-watch and
wallpaper daemon still bound to the dead instance.

## Touch selection on pocket4: the pointer-motion traps (2026-09-17)

- **`hyprctl plugin unload` does not unload hyprgrass.** It exports ~170
  STB_GNU_UNIQUE symbols, which make the .so NODELETE: it stays mapped (check
  `/proc/$(pgrep -x Hyprland)/maps`) and its `static` touch listeners keep firing.
  An "all plugins unloaded" experiment is therefore invalid, and a rebuilt
  hyprgrass only takes effect after a Hyprland restart. hyprexpo does unmap.
- **Chromium hides touch-selection handles and its Cut/Copy bar on ANY
  wl_pointer.enter/motion.** Any compositor or plugin code that re-sends the
  pointer during touch input breaks handle drags. Two such sources were fixed:
  hyprgrass's touch-down `refocus()` (fork branch `pocket4-hyprland-0.56.2`) and
  Hyprland's `simulateMouseMovement` on surface unmap (`packages/hyprland/`).
- **pocket4 runs a patched `hyprland 0.56.2-3.1`**, built by `install.sh` through
  `packages/install-patched` (profile `[packages] patched`). A system upgrade to a
  newer Arch hyprland replaces it (handle drags break), and the next `install.sh`
  then stops with rebase instructions; see `packages/hyprland/README.md`.
- `pacman -S --needed hyprland` DOWNGRADES a locally built 3.1 back to the repo's
  3 (checked with `--print`), which is why install.sh keeps patched names out of
  its pacman -S.
- Useful probes: a uinput multitouch device (legacy `uinput_user_dev` written to
  the fd, INPUT_PROP_DIRECT, no Hyprland device config, so normalised positions
  map straight onto the logical monitor box); a local page POSTing
  pointer/touch/selectionchange events; `WAYLAND_DEBUG=1` on foot or a throwaway
  `brave --user-data-dir=<tmp>`; `obsidian eval code=...` for Obsidian state.
  `wtype -M shift -s MS -m shift` holds Shift for pointer-emulation tests.
- `uwsm app -- obsidian` started a unit that exited immediately, twice, with no
  log; `/usr/bin/obsidian` launched directly worked. Not investigated.

## Nothing Ear (a) on pocket4: why "connect" fails the first time (2026-09-18)

Captured with btmon on a failing connect (the capture shows the real cause; the
journal only says `Function not implemented (38)`, which is just the kernel's
catch-all for an unmapped HCI status — here 0x22 LMP Response Timeout):

- The Pocket sends its stored link key; **the earbuds reject it** (they no longer
  hold a bond for 6C:4C:E2:10:77:F4), so the controller falls straight back to
  fresh SSP pairing. The earbuds are NoInputNoOutput but ask for MITM, so the
  kernel raises a Numeric Comparison with `confirm_hint 0` — bluetoothd sends it
  to an agent and nothing answers (blueman-applet is the default agent; its
  prompt never reaches Lukas). ~25 s later: Authentication Failure / LMP timeout.
  Meanwhile the ACL + SDP are up, so tools show "Connected: yes" with no audio.
- The passkey is theatre: the resulting key is type 4 (Unauthenticated, P-192).
- **Fix that worked without touching the earbuds (no pairing mode, no reset):**
  a throwaway python-dbus Agent1 that answers RequestConfirmation only for
  `dev_2C_BE_EB_D0_E4_9D`, registered + RequestDefaultAgent, then Device1.Connect().
  bluetoothd stores the new key and A2DP comes up. JustWorksRepairing does NOT
  help: it only applies when confirm_hint is 1.
- Windows dual-boot ruled out for the 2026-09-18 loss: Windows' SYSTEM hive was
  last written 2026-08-02; the Pocket's bond was made 2026-09-04 and lost by 09-18.
- Ear (a) stores at most 8 pairing records (Nothing support). A factory reset
  wipes the Pocket's record too, which guarantees the next Pocket connect fails.
  Why the earbuds dropped the Pocket (list eviction vs reset) is NOT established.

### Dictation through the Ear (a) mic is unreliable, and it is the earbuds' audio

Measured 2026-09-18 over 11 Super+D attempts: about half typed a partial
sentence, the rest typed nothing. Everything on the Pocket side was cleared:

- **Voxtype hears exactly what PipeWire delivers.** Verified by teeing Voxtype's
  ALSA capture to a file (a runtime-only `voxtype.service.d` drop-in with
  `-c <copy of config.toml with device = "voxtap">` and
  `ALSA_CONFIG_PATH=/usr/share/alsa/alsa.conf:<conf defining pcm.voxtap { type
  file; slave.pcm "default"; file ...; format raw }>`; cpal finds it by hint name)
  while `parecord -d bluez_input.2C:BE:EB:D0:E4:9D` recorded in parallel. Both
  copies have the same per-second peaks and transcribe the same way. Voxtype
  captures at 44.1 kHz stereo F32; both channels are identical copies of the mono
  HFP source, so the stereo request loses nothing.
- **Level is not the problem.** Parakeet still transcribed a good earbud clip
  attenuated by 12 dB (rms -48 dBFS) and partially at -18 dB; boosting a failed
  clip by 20 dB did not rescue it. `[vad] enabled = false`, so nothing filters.
- **The audio itself is fragmentary.** Lukas listened to two failed captures
  played back: "only heard bits and pieces". Some captures have holes of digital
  silence mid-speech (24% dead 7.5 ms frames, one 390 ms hole); others are
  continuous but mangled. Scripted sentence "The quick brown fox jumps over the
  lazy dog, one two three four five" came out as "Quick brown fox jumps on the
  lazy dog." / "The quick and box jumps on the five." / "". Parakeet flips
  between a partial sentence and "" on a one-second difference of quiet tail.
- Not it: 2.4 GHz coexistence (Wi-Fi on 5200 MHz), adapter quirks (Intel AX210
  8087:0032 has none in bluez-hardware.conf), kernel `corrupted SCO packet`
  (11 at 14:01:41 during forced profile switches, none during the attempts).
- No hardware mic-gain knob: PipeWire 1.6.8 only sends `+VGM` after the HF
  reports `AT+VGM=` (backend-native.c, `rfcomm_emit_volume_changed`); the Ear (a)
  sends only `AT+VGS=7` (BRSF=1023), so PipeWire never controls its mic gain.
- The 2026-09-04 "-27.45 dBFS, peak 20235" figure was Lukas speaking for a
  gain test; normal speech through these buds lands at -36 to -45 dBFS. Not a
  regression.

Untested next steps: CVSD vs mSBC with the scripted sentence (`pactl
set-card-profile bluez_card.2C_BE_EB_D0_E4_9D headset-head-unit-cvsd`), the
WH-1000XM4's HFP mic on the same Pocket (separates link from earbuds), btusb
`enable_autosuspend=Y` (AX210 BT is on `power/control=auto`), and the earbuds'
own voice processing in the Nothing X app. Workaround that works: Super+Ctrl+I
onto the built-in mic while the buds stay the output.

### Test hygiene learned the hard way

- Play beeps through the earbuds before a test that needs Lukas to speak, and
  wait for his "go" (memory `audible-cue-for-hands-on-tests`). Three captures
  were wasted before that.
- Give him the sentence to say, so the transcript can be scored.
- Do not kill the harness shell: `pkill -f <script>` matches the `zsh -c` that
  runs the tool call itself (exit 144). Use the background task's id instead.
- **`myrig-reinstall` restarts supervisord, which kills the sesh work tmux
  server and every thread in it** — this session died twice (14:09:25,
  14:26:04) from a fleet reinstall pushed over Tailscale SSH from another
  machine (`git pull && myrig-reinstall`). Check `pgrep -af myrig-reinstall`
  before blaming anything else for a session crash on pocket4.

## Lock-screen wake lag: initial investigation (2026-09-25; not fixed)

- Last sleep was Sep 23 09:00 → Sep 25 22:18 (~61h19m), s2idle, kernel
  6.18.52-1-lts. hyprlock 0.9.6-3 (upstream latest release July 18), hypridle
  0.1.8-2, Hyprland 0.56.2-3.1, Mesa 26.2.3.
- Confirmed avoidable contribution: `/usr/lib/systemd/system-sleep/pocket4-mode`
  (identical to `~/mysetup/gpd-fanctl/pocket4-mode-sleep`) sleeps 3 seconds, then
  synchronously restarts pocket4-mode.service. systemd freezes user.slice until
  ALL post hooks finish. Last resume: returned 22:18:48.579 → thawed
  22:18:51.774 (3.195 s). Repeated on earlier resumes. Fix would preserve the
  delayed power-limit reapply but schedule it outside the blocking sleep hook;
  do not just delete the power restoration or disable systemd's freezer.
- That does NOT explain a GUI stall after remote sesh is already usable:
  MacBook cockpit reattached at 22:18:58.934. Authentication failure logged
  at 22:19:49, but no record of when typing began or frames appeared, so the
  intervening time must NOT be labelled measured lock-screen latency.
- hypridle runs via `uwsm app` SCOPE, not hypridle.service. Its fd 1 and 2
  point to /dev/null; lock command is `pidof hyprlock || hyprlock`. Need
  journal logging for both processes before claiming a precise root cause.
  Hyprland log also lacks useful timestamped lock/wake traces here.
- Live lock config: solid color + $TIME + password input, no wallpaper/blur
  or shell widgets. Defaults still enable animations and fade_on_empty.
  v0.9.6 screencopyRequired() captures desktop for fade animations even with
  a solid-color background. A no-animation/always-visible-input A/B test is
  plausible, NOT a demonstrated fix. No settings changed or lock tests run.
- GPU resumed successfully with no timeout/reset in this wake. Currently
  0 swap used, 14GiB available, no CPU/IO/memory pressure, compositor IPC
  median 5.4ms (15 calls); current health does not prove wake-time health.
- Upstream leads (not diagnoses): hyprlock#700 (Mar 2025, delayed focus,
  maintainer calls it Hyprland-side); #1030/#1033 (May/Jun 2026, frozen input
  rendering, NVIDIA-specific evidence, not a match for this AMD machine);
  #1071 (Sep 14 2026, v0.9.6 $TIME resource completion race, clock-only).
  hypridle#146 maintainer recommends --no-fade-in before suspend; current
  hypridle auto-inhibit source already recognizes this config's
  loginctl lock-session + hyprlock combination, so inhibit_sleep=3 is not
  automatically a fix.
- Next: clarify black screen vs delayed dots vs post-Enter delay, enable
  non-keystroke journal diagnostics, then controlled lock-only / DPMS /
  suspend comparisons with Lukas's go. Never capture real password keycodes
  via WAYLAND_DEBUG or evdev logging.

### Live recurrence, 2026-09-26 ~21:56–22:00 (still not diagnosed)

- Lukas reported all keypresses unresponsive. hyprlock PID 2296467 had been
  running ~6h15m; last system suspend ended 15:31, so this occurrence was
  NOT a fresh system resume. DPMS was on, compositor IPC healthy.
- A 12-second aggregate EV_KEY counter saw 42 events from keyd's virtual
  keyboard (event17) while he pressed Shift. Never printed/stored keycodes or
  values. This proves delivery to the virtual device, NOT to hyprlock.
- Brief batch gdb attaches to HYPRLOCK ONLY, stack args disabled, detached
  normally. Symbolized main thread waiting in CHyprlock::run condition variable;
  lock acquired/locked both true, not fading/terminating. Single output surface
  readyForFrame=true, needsFrame=false, frameCallback=null. No GPU wait at
  sampling time. Do not overclaim this excludes all rendering/event-loop races.
- Asked to move trackpad/click password box, then Shift. Initially still stuck;
  shortly afterward Lukas reported it working and unlocked (~22:00). No action
  can be credited as the fix. No restart, signal, or focus change was injected.
- Enabled normal journaling at source: hypridle autostart through
  `uwsm app -- systemd-cat -t hypridle hypridle`; its lock_cmd uses
  `pidof hyprlock || systemd-cat -t hyprlock hyprlock`. No WAYLAND_DEBUG or
  key tracing. Deployed with `./install.sh --profile pocket4 --config-only`,
  restarted only hypridle at 22:02 (PID 2753473). Confirmed sleep inhibition
  still recognizes the wrapped lock command. 29 tests pass; configerrors empty.
- Prepared `/tmp/pocket4-lock-focus.py`: read-only /proc/PID/mem snapshots of
  compositor seat focus, session-lock surfaces, and m_lastInputTouch; NO debugger
  attached to compositor, no input/password buffers. Exact build-ID guard.
  Offsets derived OFFLINE from locally cached hyprland-debug 0.56.2-3.1 package
  extracted to /tmp/pocket4-hyprland-symbols (514MB; clean up after testing).
  It was ready only AFTER recovery, so there is no stuck-state focus snapshot.
- Concrete UNTESTED lead: local simulateMouseMovement touch patch can skip
  the synthetic movement SessionLockManager.cpp relies on to focus a newly
  mapped lock surface. Read m_lastInputTouch + focus during next lock; test
  touch-last vs pointer-last. Real pointer movement should ordinarily recover
  that case, so it doesn't yet explain the whole observed delay.
- Controlled pointer-last lock/DPMS test, 22:06:45–22:06:53: locked session 3,
  DPMS off for five seconds, then on. Keyboard and pointer focus matched the
  mapped lock surface before/off/after; m_lastInputTouch=false throughout.
  Lukas confirmed password dots appeared immediately. This single trial did
  NOT reproduce the failure; it does not rule out intermittent DPMS trouble.
  Resources gathered in 6ms; onLockLocked at 22:06:45.688, confirming logging
  and lock-notify inhibition work. From this remote agent `loginctl lock-session`
  without an ID fails (no auto session); use verified desktop session 3.
- Next: touch-last lock comparison. server-mode currently inhibits suspend;
  do NOT bypass that without coordination. Animations unchanged; power hook
  not yet changed.
