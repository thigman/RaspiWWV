#!/bin/bash
#
# Test the RTC and Audio
#
#


# OLED test is optional: run  python3 ./testOLED.py  if you installed the OLED (installOLED.sh)

echo
echo "Testing RTC..."
sudo hwclock -r
timedatectl status
echo
echo "You should see current RTC Date/Time in UTC"
sleep 2

echo "Testing Audio..."
sudo amixer sset PCM,0 95%
aplay /usr/share/sounds/alsa/Front_Center.wav
mpg123 sounds/wwv_at_the_tone.mp3
echo
echo "You should have heard audio"
echo
sleep 2

