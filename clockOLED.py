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
        bar_top = device.height - 6
        draw.rectangle((0, bar_top, device.width - 1, device.height - 1), outline="white")
        elapsed = now.second + now.microsecond / 1_000_000
        filled = int((device.width - 2) * elapsed / 60)
        if filled:
            draw.rectangle((1, bar_top + 1, filled, device.height - 2), fill="white")

        clock_x = max(8, min(device.width - 9, filled))
        clock_y = bar_top - 9
        draw.ellipse(
            (clock_x - 8, clock_y - 8, clock_x + 8, clock_y + 8),
            outline="white",
        )
        draw.line(
            [(clock_x, clock_y - 6), (clock_x, clock_y - 3), (clock_x + 3, clock_y - 3)],
            fill="white",
        )
        draw.point([(clock_x - 3, clock_y), (clock_x + 3, clock_y)], fill="white")
        draw.line(
            [(clock_x - 3, clock_y + 3), (clock_x - 2, clock_y + 4),
             (clock_x + 2, clock_y + 4), (clock_x + 3, clock_y + 3)],
            fill="white",
        )
    time.sleep(0.1)
