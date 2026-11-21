#!/usr/bin/env python3
#
# SSD1309 SPI OLED clock
# License: GPLv3, see: www.gnu.org/licenses/gpl-3.0.html

import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw

CALIFORNIA = ZoneInfo("America/Los_Angeles")
COLORADO = ZoneInfo("America/Denver")

SMALL_FONT = {
    " ": ("000", "000", "000", "000", "000"),
    "-": ("000", "000", "111", "000", "000"),
    ":": ("000", "010", "000", "010", "000"),
    "0": ("111", "101", "101", "101", "111"),
    "1": ("010", "110", "010", "010", "111"),
    "2": ("110", "001", "010", "100", "111"),
    "3": ("110", "001", "010", "001", "110"),
    "4": ("101", "101", "111", "001", "001"),
    "5": ("111", "100", "110", "001", "110"),
    "6": ("011", "100", "110", "101", "010"),
    "7": ("111", "001", "010", "010", "010"),
    "8": ("010", "101", "010", "101", "010"),
    "9": ("010", "101", "011", "001", "110"),
    "A": ("010", "101", "111", "101", "101"),
    "C": ("011", "100", "100", "100", "011"),
    "E": ("111", "100", "110", "100", "111"),
    "I": ("111", "010", "010", "010", "111"),
    "M": ("101", "111", "111", "101", "101"),
    "O": ("010", "101", "101", "101", "010"),
    "T": ("111", "010", "010", "010", "010"),
    "U": ("101", "101", "101", "101", "111"),
}

SEGMENTS = {
    "0": "abcdef",
    "1": "bc",
    "2": "abged",
    "3": "abgcd",
    "4": "fgbc",
    "5": "afgcd",
    "6": "afgecd",
    "7": "abc",
    "8": "abcdefg",
    "9": "abfgcd",
}


def draw_small_text(draw, text, x, y):
    for char in text:
        for row, pixels in enumerate(SMALL_FONT[char]):
            for col, pixel in enumerate(pixels):
                if pixel == "1":
                    draw.point((x + col, y + row), fill="white")
        x += 4


def draw_led_time(draw, text, x, y):
    for char in text:
        if char == ":":
            draw.rectangle((x, y + 7, x + 1, y + 8), fill="white")
            draw.rectangle((x, y + 17, x + 1, y + 18), fill="white")
            x += 5
            continue

        rectangles = {
            "a": (x + 2, y, x + 9, y + 1),
            "b": (x + 10, y + 2, x + 11, y + 10),
            "c": (x + 10, y + 14, x + 11, y + 22),
            "d": (x + 2, y + 23, x + 9, y + 24),
            "e": (x, y + 14, x + 1, y + 22),
            "f": (x, y + 2, x + 1, y + 10),
            "g": (x + 2, y + 11, x + 9, y + 12),
        }
        for segment in SEGMENTS[char]:
            draw.rectangle(rectangles[segment], fill="white")
        x += 14


def render_clock(now):
    image = Image.new("1", (128, 64), 0)
    draw = ImageDraw.Draw(image)

    colorado = now.astimezone(COLORADO).strftime("CO TIME: %H:%M")
    california = now.astimezone(CALIFORNIA).strftime("CA TIME: %H:%M")
    draw_small_text(draw, colorado, 0, 2)
    draw_small_text(draw, california, 128 - (len(california) * 4 - 1), 2)

    utc = now.astimezone(timezone.utc)
    draw_small_text(draw, "UTC:", 3, 28)
    draw_led_time(draw, utc.strftime("%H:%M:%S"), 25, 18)
    date = utc.strftime("%Y-%m-%d")
    draw_small_text(draw, date, 0, 52)

    draw.line((53, 52, 53, 54), fill="white")
    draw.line((53, 54, 51, 56), fill="white")
    draw.line((53, 54, 55, 56), fill="white")
    draw.point((50, 52), fill="white")
    draw.point((56, 52), fill="white")

    if utc.microsecond < 500_000:
        draw.polygon(
            [(68, 54), (77, 52), (75, 54), (84, 52),
             (80, 56), (81, 54), (73, 56), (74, 54)],
            fill="white",
        )

    draw.rectangle((106, 52, 120, 56), outline="white")
    draw.rectangle((108, 53, 110, 55), outline="white")
    draw.line((114, 53, 118, 53), fill="white")
    draw.point((116, 54), fill="white")
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
