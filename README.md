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
not the RTC directly. Configure the OS RTC and time synchronization separately.
The installer adds a timer that updates `/dev/rtc0` only after the system
reports synchronized time and the date is in the safe range described below.

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

### Automatic RTC updates

The RTC must already be configured as the system hardware clock. For the Seeed
DS1307, confirm `sudo hwclock -r -f /dev/rtc0` works and configure the OS to use
UTC for the RTC (`timedatectl` should report `RTC in local TZ: no`). The system
must also have a working NTP synchronization service configured; the installer
does not enable or replace one.

The installer enables `raspiwwv-rtc.timer`. It first checks 15 seconds after
boot and retries one minute after each check, even if an earlier write
succeeded. When `/dev/rtc0` exists, `timedatectl` reports
`NTPSynchronized=yes`, and UTC is between 2024-01-01 inclusive and 2100-01-01
exclusive, the root-run service executes `hwclock -w -f /dev/rtc0`. The
lower bound rejects obviously old dates; the upper bound reflects the DS1307's
2000-2099 year range. Neither bound proves that a synchronized clock is
accurate: the configured time source must be trustworthy.

With no synchronized time or no `/dev/rtc0`, the service skips the write and
tries again later. There is no battery-installed marker: after the recipient
installs the battery, a later synchronized check can update the RTC. The service
does not read the RTC into the system clock or change the OS boot-time RTC
setup; an offline Pi relies on its normal RTC initialization. A missing or
depleted battery may leave the RTC unable to retain time while powered off.
Linux or other time services may also write the RTC independently (for example,
the kernel's synchronized 11-minute update); this service does not control
those writers. `updateRTCtoNTP.sh` now runs the same guarded check instead of
testing network connectivity; it requires `installWWV.sh` to have installed the
root-owned check first. Rerun `installWWV.sh` after pulling changes to
`sync_rtc.py` to install the updated copy.

```sh
systemctl status raspiwwv-rtc.timer
timedatectl show --property=NTPSynchronized --value
journalctl -u raspiwwv-rtc.service -b --no-pager
```

### Optional SSD1309 SPI OLED

`clockOLED.py` uses SPI port 0, device 0, GPIO 25 for DC and GPIO 27 for reset
(BCM numbering). Enable SPI, ensure the Pi user has access to SPI and GPIO, and
install `luma.oled`, Pillow, SPI and GPIO dependencies in the Python environment.
The display shows California and Colorado local time (including daylight
saving changes) above a 24-hour UTC clock with seconds and the UTC date.
Beside the date, an antenna and radio are connected by a bolt that flashes
once per second.
After the first successful RTC write in a boot, the OLED shows `RTC SYNCED` for
15 seconds, then returns to the clock. If the OLED starts after that write, it
shows the alert at startup. The notification is stored in `/run` until reboot
and never prevents later RTC writes. A successful write does not prove that the
battery is installed or that the RTC will retain time without power.
The system must have the IANA time zone database installed (the `tzdata`
package on Raspberry Pi OS).
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
