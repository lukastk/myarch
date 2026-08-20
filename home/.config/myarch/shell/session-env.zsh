# Graphical session environment self-heal (sesh issue #10, part B — the sesh
# daemon half, which injects this same whitelist into thread panes at spawn
# time via tmux -e, is commit 52c58a9 in the sesh repo).
#
# Shells that start without the graphical session environment — ssh sessions,
# panes on the boot-started sesh work tmux server (started before login by
# sesh-daemon), agent tool shells inside such panes — otherwise see a void:
# no WAYLAND_DISPLAY / XDG_SESSION_TYPE / DISPLAY / HYPRLAND_INSTANCE_SIGNATURE,
# so anything they launch that touches the session breaks (Chromium/Electron
# fall back to X11: cold-launched brave --app windows come up XWayland with
# the generic Brave-browser class, floating, matching no windowrule; Slack /
# Signal abort with "Missing X server or $DISPLAY"; hyprctl can't find the
# compositor instance).
#
# uwsm/Hyprland publish the canonical session env to the systemd user
# manager's activation environment at session start (uwsm finalize; refreshed
# on every compositor start), and it is reachable from any boot-context shell:
# systemctl --user derives the bus from XDG_RUNTIME_DIR alone. So: when this
# shell is missing the session vars, import the whitelist from there.
#
# Gated so in-session shells skip it entirely (one systemctl fork, ~5-15ms,
# only for env-less shells). Absence of a session (ssh before first login,
# headless) is legitimate — the query yields nothing and the shell proceeds
# without the vars, exactly as before.
if [ -z "${WAYLAND_DISPLAY:-}" ] || [ -z "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]; then
	if [ -S "/run/user/$UID/bus" ] && command -v systemctl >/dev/null 2>&1; then
		while IFS='=' read -r _senv_k _senv_v; do
			export "$_senv_k=$_senv_v"
		done < <(systemctl --user show-environment 2>/dev/null | grep -E '^(WAYLAND_DISPLAY|DISPLAY|XDG_RUNTIME_DIR|XDG_SESSION_TYPE|XDG_SESSION_CLASS|XDG_CURRENT_DESKTOP|XDG_SESSION_DESKTOP|DBUS_SESSION_BUS_ADDRESS|HYPRLAND_INSTANCE_SIGNATURE)=')
		unset _senv_k _senv_v
	fi
fi
