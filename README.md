WWV Simulator
========


![RaspiWWV](/sample.jpg)

Raspberry Pi WWV Simulator

Recreates the WWV Shortwave audio broadcast time signal
without requiring a radio or even Internet access.
This syncronizes the Pi audio to a local Real-Time Clock (RTC)
playing the correct time like WWV.

Hear it in action on [YouTube](https://youtu.be/FzX1HpYpx6E)

Actually, this is a project to help show you how to connect a tiny OLED screen, a Real Time Clock (RTC) and/or an Audio Amplifier all to a single Raspberry Pi Zero!  All with the bonus of being able to listen to WWV time “signals” anytime you wish. 

ACCURACY:
The Pi's clock is set to the RTC so is as accurate as the RTC
module. (Typically, +-1 second or so per day)
For more accuracy, use a higher quality RTC module.

Note that the Pi will automatically recalibrate the RTC
whenever it is connected to the Internet (ethernet or wifi)

Also Note: It can take up to two minutes before audio starts (for syncronization)

INSTRUCTIONS:
[RaspiWWV.pdf](/RaspiWWV.pdf)



Installs the reboot cron and startup file. (This assumes installed to /home/pi on Raspberry.)

Requires Python 3 (default on current Raspberry Pi OS). Install with `sh installWWV.sh`.

The OLED display is optional. `clockOLED.py` uses an SSD1309 SPI display with
SPI port 0, device 0, GPIO 25 for DC, and GPIO 27 for reset (BCM pin numbers).
Enable SPI and use a Python environment with `luma.oled`, Pillow, SPI and GPIO
support installed. Test the clock with `python3 clockOLED.py` in that environment.
The bar at the bottom fills over each UTC minute and resets at the next minute.
`runWWV.sh` starts it alongside the simulator using the system `python3`, so
that interpreter must have the OLED dependencies too.

`installOLED.sh` and `testOLED.py` are for the original SSD1306 I2C display;
they do not set up or test the SSD1309 SPI clock.

Manually run WWV Simulator using:

    $ sh runWWV.sh

