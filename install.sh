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
    xdg-desktop-portal-hyprland xdg-desktop-portal-gtk
    waybar wofi mako libnotify
    grim slurp hyprpicker cliphist wl-clipboard
    tesseract tesseract-data-eng zbar gpu-screen-recorder ffmpeg ffmpegthumbnailer
    brightnessctl hyprsunset playerctl pavucontrol pipewire-alsa
    network-manager-applet networkmanager blueman bluez bluez-utils bluetui
    kitty foot xdg-utils
    ttf-jetbrains-mono-nerd noto-fonts noto-fonts-emoji noto-fonts-cjk
    ttf-nerd-fonts-symbols ttf-nerd-fonts-symbols-common otf-font-awesome gsfonts
    keyd python-jinja jq fzf shellcheck util-linux cpio cmake git meson ninja pkgconf glm
  )
  sudo pacman -S --noconfirm --needed "${packages[@]}"

  if ! command -v paru >/dev/null 2>&1; then
    echo "Voxtype installation requires paru for the official voxtype-bin AUR package" >&2
    exit 1
  fi
  paru -S --noconfirm --needed voxtype-bin
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
