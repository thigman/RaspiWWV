# WWV Simulator

![RaspiWWV](/sample.jpg)

Raspberry Pi WWV Simulator recreates the WWV shortwave time signal using the
Pi's UTC clock, without requiring a radio or Internet access. An RTC can keep
time while the Pi is offline. Accuracy depends on the RTC and system clock.
Hear it in action on [YouTube](https://youtu.be/FzX1HpYpx6E). Hardware and
original setup instructions are in [RaspiWWV.pdf](/RaspiWWV.pdf).

## Start automatically at boot

First configure and test the audio hardware and, if used, the RTC. Make sure
`timedatectl status` shows the correct time; the services use the system clock,
not the RTC directly. Configure the OS RTC and time synchronization separately:
the services do not set or write the clock. The old `updateRTCtoNTP.sh` only
checks network connectivity, not whether time is synchronized, so it is not
run at startup.

Run these commands as the normal Pi user from the repository directory. The
user needs access to the audio device. The installer uses sudo, installs
`alsa-utils` and `mpg123`, and creates a systemd service pointing to this
checkout and Python interpreter. Keep the checkout in place.

If upgrading from the old cron installation, use `crontab -e` to remove its
`@reboot ... runWWV.sh` entry first. Also remove any separately installed
root-crontab entry or other startup job for the old launcher; otherwise multiple
players may compete for the device. The installer does not replace your crontab.

```sh
./installWWV.sh
sudo systemctl status raspiwwv-audio.service
```

Audio begins on the next UTC minute boundary. Test the audio device separately
with `aplay /usr/share/sounds/alsa/Front_Center.wav`. The service starts at boot
and restarts after a failure, including a player error or a player that hangs.
The journal retains errors rather than discarding them.

### Optional SSD1309 SPI OLED

`clockOLED.py` uses SPI port 0, device 0, GPIO 25 for DC and GPIO 27 for reset
(BCM numbering). Enable SPI, ensure the Pi user has access to SPI and GPIO, and
install `luma.oled`, Pillow, SPI and GPIO dependencies in the Python environment.
The center of the display shows UTC in 24-hour `UTC: HH:MM:SS` format.
For example, on Raspberry Pi OS, enable SPI in `sudo raspi-config` under
Interface Options, then create a virtual environment:

```sh
sudo apt-get install -y python3-venv python3-pil python3-dev python3-spidev python3-rpi.gpio build-essential
python3 -m venv --system-site-packages .venv
.venv/bin/pip install luma.oled
.venv/bin/python clockOLED.py
```

Stop the manual test with Ctrl+C, then install both services using the same
interpreter:

```sh
PYTHON="$PWD/.venv/bin/python" ./installWWV.sh --oled
sudo systemctl status raspiwwv-oled.service
```

To use a virtual environment for both services, run
`PYTHON=/absolute/path/to/venv/bin/python ./installWWV.sh --oled`. The
environment and checkout must be accessible to the Pi user at boot. The OLED
and audio are separate services, so one can restart without stopping the other.
To disable the display later, run `sudo systemctl disable --now raspiwwv-oled.service`.
`installOLED.sh` and `testOLED.py` are for the original SSD1306 I2C display,
not this SSD1309 SPI clock.

## Troubleshooting

```sh
journalctl -u raspiwwv-audio.service -b --no-pager
journalctl -u raspiwwv-audio.service -b -1 --no-pager
journalctl -u raspiwwv-oled.service -b --no-pager
sudo systemctl restart raspiwwv-audio.service
```

The `-b -1` command shows the previous boot if the journal is persistent. If the
audio fails overnight, save the journal around the failure and check power,
audio device and amplifier connections. Player exit codes and timeouts are
reported, but software cannot detect a disconnected speaker, silent amplifier,
or a player that runs normally while producing no audible sound. Restarting a
service cannot fix those hardware faults. A completely hung OLED process is
not detected by systemd's process restart policy. On an offline Pi, verify clock
and RTC accuracy independently.
