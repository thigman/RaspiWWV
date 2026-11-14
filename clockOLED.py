#!/usr/bin/env python3
#
# SSD1309 SPI OLED clock
# License: GPLv3, see: www.gnu.org/licenses/gpl-3.0.html

import time
from datetime import datetime, timezone
from pathlib import Path

from PIL import ImageFont
from luma.core.interface.serial import spi
from luma.core.render import canvas
from luma.oled.device import ssd1309

serial = spi(
    port=0,
    device=0,
    gpio_DC=25,
    gpio_RST=27,
    bus_speed_hz=8000000,
)
device = ssd1309(serial)

font = ImageFont.load_default()
time_font = ImageFont.truetype(
    str(Path(__file__).parent / "fonts" / "VCR_font.ttf"), 16
)

while True:
    now = datetime.now(timezone.utc)
    with canvas(device) as draw:
        draw.text((0, 0), now.strftime("%Y-%m-%d"), font=font, fill="white")
        draw.text((0, 16), now.strftime("%H:%M:%S UTC"), font=time_font, fill="white")
    time.sleep(0.1)
