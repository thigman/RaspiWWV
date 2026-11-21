#!/usr/bin/env python3
#
# SSD1309 SPI OLED clock
# License: GPLv3, see: www.gnu.org/licenses/gpl-3.0.html

import time
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT_DIR = Path(__file__).parent / "fonts"
VCR_FONT = str(FONT_DIR / "VCR_font.ttf")


def draw_centered_text(draw, box, text, font):
    left, top, right, bottom = box
    bbox = draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    x = left + (right - left - width) // 2
    y = top + (bottom - top - height) // 2 - bbox[1]
    draw.text((x, y), text, font=font, fill="white")


def render_clock(now):
    image = Image.new("1", (128, 64), 0)
    draw = ImageDraw.Draw(image)
    small_font = ImageFont.load_default()
    utc_font = ImageFont.truetype(VCR_FONT, 14)

    draw.rectangle((1, 1, 62, 13), outline="white")
    draw.rectangle((65, 1, 126, 13), outline="white")
    draw.text((4, 2), "CA TIME", font=small_font, fill="white")
    draw.text((67, 2), "CO TIME", font=small_font, fill="white")
    draw.text((4, 7), "California", font=small_font, fill="white")
    draw.text((67, 7), "Colorado", font=small_font, fill="white")

    draw.rectangle((1, 15, 126, 47), outline="white")
    utc_time = now.astimezone(timezone.utc).strftime("UTC: %H:%M:%S")
    draw_centered_text(draw, (2, 16, 125, 46), utc_time, utc_font)

    draw.rectangle((1, 49, 20, 62), outline="white")
    draw.rectangle((107, 49, 126, 62), outline="white")

    draw.line((10, 50, 10, 53), fill="white")
    draw.line((10, 53, 6, 61), fill="white")
    draw.line((10, 53, 14, 61), fill="white")
    draw.line((8, 57, 12, 57), fill="white")
    draw.line((7, 61, 13, 61), fill="white")
    draw.line((8, 57, 13, 61), fill="white")
    draw.line((12, 57, 7, 61), fill="white")
    draw.line((3, 50, 7, 53, 5, 53, 7, 55), fill="white")
    draw.line((17, 50, 13, 53, 15, 53, 13, 55), fill="white")

    draw.text((109, 50), "CART", font=small_font, fill="white")
    draw.text((109, 54), "RAD", font=small_font, fill="white")
    draw.text((109, 58), "RX", font=small_font, fill="white")

    draw.rectangle((23, 49, 104, 62), outline="white")
    draw_centered_text(draw, (24, 49, 103, 62), "1 SEC BLINK", small_font)

    if now.second % 2 == 0:
        bolt_x = 96
        bolt_y = 50
        draw.polygon(
            [(bolt_x - 2, bolt_y), (bolt_x - 6, bolt_y + 6),
             (bolt_x - 3, bolt_y + 6), (bolt_x - 5, bolt_y + 12),
             (bolt_x + 3, bolt_y + 4), (bolt_x, bolt_y + 4),
             (bolt_x + 2, bolt_y)],
            fill="white",
        )

    return image


def main():
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

    while True:
        now = datetime.now(timezone.utc)
        with canvas(device) as draw:
            draw.bitmap((0, 0), render_clock(now), fill="white")
        time.sleep(0.1)


if __name__ == "__main__":
    main()
