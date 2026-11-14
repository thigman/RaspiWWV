#!/bin/bash

cd /home/pi/RaspiWWV;
sudo sh updateRTCtoNTP.sh

# Start the optional OLED display alongside the simulator.
python3 clockOLED.py &
python3 wwv_simulator.py 
#sudo shutdown --no-wall now

