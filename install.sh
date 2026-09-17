#!/usr/bin/env bash
set -euo pipefail

if [[ $(uname -s) != Linux ]] || [[ ! -f /etc/arch-release ]]; then
  echo "myarch supports Arch Linux only" >&2
  exit 1
fi

profile=""
theme=""
config_only=false
skip_runtime=false

while (($#)); do
  case "$1" in
    --profile)
      (($# >= 2)) || { echo "--profile requires pocket4 or ideapad" >&2; exit 2; }
      profile=$2
      shift 2
      ;;
    --theme)
      (($# >= 2)) || { echo "--theme requires a theme name" >&2; exit 2; }
      theme=$2
      shift 2
      ;;
    --config-only)
      config_only=true
      shift
      ;;
    --skip-runtime)
      skip_runtime=true
      shift
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

case "$profile" in
  pocket4|ideapad) ;;
  *) echo "--profile must be pocket4 or ideapad" >&2; exit 2 ;;
esac

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

if [[ $config_only == false ]]; then
  packages=(
    hyprland uwsm hyprpaper hyprlock hypridle hyprpolkitagent
    # Arch split hyprpm out of the hyprland package in 0.56.2-3; install.py's
    # plugin step and the autostart's `hyprpm reload` both need it.
    hyprpm
    xdg-desktop-portal-hyprland xdg-desktop-portal-gtk
    # A Wine/Proton game under XWayland misplaces its fullscreen rectangle and
    # leaks the pointer whenever two outputs are live; `display-mode external`
    # (or `internal`) is the usual fix, and gamescope is the fallback for when
    # neither is wanted — `gamescope -W <w> -H <h> -f -- %command%` as a Steam
    # launch option nests the game in its own single-output display whatever the
    # layout is. See home/.mybin/display-mode for the whole problem.
    gamescope
    waybar fuzzel mako libnotify
    grim slurp hyprpicker cliphist wl-clipboard
    tesseract tesseract-data-eng zbar gpu-screen-recorder ffmpeg ffmpegthumbnailer
    brightnessctl hyprsunset playerctl pavucontrol pipewire-alsa
    network-manager-applet networkmanager blueman bluez bluez-utils bluetui
    kitty foot xdg-utils
    noto-fonts noto-fonts-emoji noto-fonts-cjk
    ttf-nerd-fonts-symbols ttf-nerd-fonts-symbols-common otf-font-awesome gsfonts
    keyd python-jinja jq fzf shellcheck util-linux cpio cmake git meson ninja pkgconf glm
  )
  sudo pacman -S --noconfirm --needed "${packages[@]}"

  if ! command -v paru >/dev/null 2>&1; then
    echo "myarch desktop application installation requires paru for AUR packages" >&2
    exit 1
  fi
  paru -S --noconfirm --needed ticktick voxtype-bin
fi

args=(--profile "$profile")
if [[ -n $theme ]]; then
  args+=(--theme "$theme")
elif [[ ! -s $HOME/.config/myarch/theme ]]; then
  args+=(--theme arthur)
fi
[[ $config_only == true ]] && args+=(--config-only)
[[ $skip_runtime == true ]] && args+=(--skip-runtime)

exec python3 "$repo/install.py" "${args[@]}"
