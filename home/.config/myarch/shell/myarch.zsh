# Hyprland desktop shell helpers (Wayland twin of remote_desktop.sh's X11
# xclip aliases and the macbook spacework aliases).

# pbcopy/pbpaste over wl-clipboard. FUNCTIONS, NOT ALIASES — the same trap
# remote_desktop.sh documents, and one that actually bit us:
#
#   ~/.zshenv sources ~/.myrig/zshenv/**/*.sh in GLOB (alphabetical) order, so
#   all.sh is parsed BEFORE hyprland.sh. zsh expands aliases at PARSE time, so
#   `pbcopy` inside all.sh's y()/yy() was stored UNEXPANDED and died at call
#   time with "command not found: pbcopy" on every Hyprland machine. Functions
#   resolve at CALL time, so source order stops mattering.
#
# pbcopy also detaches wl-copy's forked selection-owner from stdout/stderr: it
# keeps running to serve the clipboard and inherits our stdio, so at the end of
# an ssh pipeline the held-open pipes would stop the session from ever closing
# (same trap as sesh-set-clipboard). Errors stay loud via a tempfile.
# WAYLAND_DISPLAY is inferred because login/ssh/popup shells do not export it.
pbcopy() {
	emulate -L zsh
	local -x WAYLAND_DISPLAY="$(_mmt_wl_display)"
	local xerr xrc
	xerr=$(mktemp) || return 1
	wl-copy >/dev/null 2>"$xerr"
	xrc=$?
	if (( xrc != 0 )); then
		print -u2 -- "wl-copy failed ($(<$xerr))"
		rm -f "$xerr"
		return $xrc
	fi
	rm -f "$xerr"
}

# -n suppresses the trailing newline wl-paste appends; macOS pbpaste adds none,
# and these are used in command substitutions where a stray newline matters.
# wl-paste does not fork, so it stays plain.
pbpaste() {
	emulate -L zsh
	local -x WAYLAND_DISPLAY="$(_mmt_wl_display)"
	wl-paste -n
}

alias open='xdg-open'

my_alias ii='~/.mybin/hypr-load-main'	-g hyprland -d 'Load main workspace layout (≙ spacework stack load main)'
my_alias ri='~/.mybin/hypr-load-main'	-g hyprland -d 'Relaunch missing workspace apps'

# Stay-awake. Same names and same interface as the macbook's (see
# ^macbook^macbook.sh), so the muscle memory carries across machines.
my_alias redbull	-g hyprland -d 'Stay awake for N hours (--screen-on also stops the screen locking)'
my_alias redbull-off	-g hyprland -d 'End the stay-awake early'
my_alias redbull-status	-g hyprland -d 'Show what is inhibiting sleep/idle, and for how long'
