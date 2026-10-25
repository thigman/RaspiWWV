#!/bin/sh
# ADAFRUIT OLED INSTALL
#
# Note: it is OK to run this script multiple times.
#
# https://learn.adafruit.com/adafruit-pioled-128x32-mini-oled-for-raspberry-pi/usage
#

# Install Deps
sudo apt-get update
sudo apt-get install -y build-essential python3-dev python3-pip python3-venv python3-pil python3-smbus python3-rpi.gpio git

# Install Libs
cd
git clone https://github.com/adafruit/Adafruit_Python_SSD1306.git
cd Adafruit_Python_SSD1306
sudo python3 setup.py install

# Test
cd 
cd RaspiWWV
python3 testOLED.py

echo
echo "Finished"
echo

