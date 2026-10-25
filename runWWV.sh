#!/bin/bash

cd /home/pi/RaspiWWV;
sudo sh updateRTCtoNTP.sh

# OLED display is optional and disabled by default (HDMI display assumed).
# To enable: python3 clockOLED.py &
python3 wwv_simulator.py 
#sudo shutdown --no-wall now

