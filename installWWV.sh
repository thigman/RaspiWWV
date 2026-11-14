#!/bin/bash
set -euo pipefail

if [[ $# -gt 1 || ( $# -eq 1 && $1 != "--oled" ) ]]; then
    echo "Usage: ./installWWV.sh [--oled]" >&2
    exit 2
fi
if [[ $(id -u) -eq 0 ]]; then
    echo "Run as the Pi user, not root; sudo will be requested when needed." >&2
    exit 1
fi

repo=$(cd -- "$(dirname -- "$0")" && pwd -P)
python=${PYTHON:-$(command -v python3)}
user=$(id -un)
for value in "$repo" "$python" "$user"; do
    if [[ $value == *['"\\%$']* || $value == *$'\n'* || $value == *$'\r'* || $value == *$'\t'* ]]; then
        echo "Paths and username must not contain quotes, backslashes, percent signs, dollar signs or control whitespace." >&2
        exit 1
    fi
done
if [[ $python != /* || ! -x $python ]]; then
    echo "PYTHON must be the absolute path to an executable Python interpreter." >&2
    exit 1
fi

# Do not overwrite or automatically edit a user's existing crontab.
if crontab -l 2>/dev/null | grep -E '^[[:space:]]*@reboot[[:space:]].*runWWV\.sh' >/dev/null; then
    echo "Remove the old @reboot runWWV.sh entry with crontab -e before installing." >&2
    exit 1
fi

if [[ ${1:-} == "--oled" ]]; then
    "$python" -c 'from PIL import Image; from luma.core.interface.serial import spi; from luma.oled.device import ssd1309'
fi

sudo apt-get update
sudo apt-get install -y alsa-utils mpg123
tmp=$(mktemp -d)
trap 'rm -f "$tmp/raspiwwv-audio.service" "$tmp/raspiwwv-oled.service"; rmdir "$tmp"' EXIT

write_unit() {
    local name=$1 script=$2 description=$3
    cat > "$tmp/$name" <<EOF
[Unit]
Description=$description
After=sound.target
StartLimitIntervalSec=0

[Service]
Type=simple
User=$user
WorkingDirectory="$repo"
ExecStart="$python" -u "$repo/$script"
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    sudo install -m 644 "$tmp/$name" "/etc/systemd/system/$name"
}

write_unit raspiwwv-audio.service wwv_simulator.py "RaspiWWV audio"
if [[ ${1:-} == "--oled" ]]; then
    write_unit raspiwwv-oled.service clockOLED.py "RaspiWWV OLED clock"
fi
sudo systemctl daemon-reload
sudo systemctl enable raspiwwv-audio.service
sudo systemctl restart raspiwwv-audio.service
if [[ ${1:-} == "--oled" ]]; then
    sudo systemctl enable raspiwwv-oled.service
    sudo systemctl restart raspiwwv-oled.service
fi
echo "Services installed. Check: systemctl status raspiwwv-audio.service"
