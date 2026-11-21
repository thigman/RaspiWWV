#!/usr/bin/env python3
#
# SSD1309 SPI OLED clock
# License: GPLv3, see: www.gnu.org/licenses/gpl-3.0.html

import logging
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

CALIFORNIA = ZoneInfo("America/Los_Angeles")
COLORADO = ZoneInfo("America/Denver")
ALERT_SECONDS = 15
SYNC_POLL_SECONDS = 2

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


class SyncAlert:
    def __init__(self):
        self._lock = threading.Lock()
        self._synchronized = None
        self._until = 0

    def update(self, synchronized, now):
        with self._lock:
            if synchronized and self._synchronized is not True:
                self._until = now + ALERT_SECONDS
            self._synchronized = synchronized

    def visible(self, now):
        with self._lock:
            return now < self._until


def ntp_synchronized():
    result = subprocess.run(
        ["timedatectl", "show", "--property=NTPSynchronized", "--value"],
        check=True, capture_output=True, text=True, timeout=3,
    )
    status = result.stdout.strip()
    if status not in ("yes", "no"):
        raise ValueError(f"Unexpected time synchronization status: {status!r}")
    return status == "yes"


def monitor_ntp(alert):
    last_error = None
    while True:
        try:
            synchronized = ntp_synchronized()
        except (OSError, subprocess.SubprocessError, ValueError) as error:
            if isinstance(error, subprocess.CalledProcessError) and error.stderr:
                detail = error.stderr.strip()
            else:
                detail = str(error)
            if detail != last_error:
                logging.warning("Cannot check NTP synchronization: %s", detail)
                last_error = detail
        else:
            if last_error is not None:
                logging.info("NTP synchronization status checks resumed")
                last_error = None
            alert.update(synchronized, time.monotonic())
        time.sleep(SYNC_POLL_SECONDS)


def render_sync_alert():
    image = Image.new("1", (128, 64), 0)
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(str(Path(__file__).parent / "fonts" / "VCR_font.ttf"), 20)
    draw.rectangle((0, 0, 127, 63), outline="white")
    for text, y in (("NTP", 7), ("SYNCED", 35)):
        left, top, right, _ = draw.textbbox((0, 0), text, font=font)
        draw.text(((128 - (right - left)) // 2 - left, y - top),
                  text, font=font, fill="white")
    return image


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

    draw.line((49, 49, 49, 61), fill="white")
    draw.line((46, 62, 52, 62), fill="white")
    draw.line([(44, 45), (42, 47), (41, 49), (41, 51), (42, 53), (44, 55)], fill="white")
    draw.line([(46, 47), (45, 48), (44, 49), (44, 51), (45, 52), (46, 53)], fill="white")
    draw.line([(54, 45), (56, 47), (57, 49), (57, 51), (56, 53), (54, 55)], fill="white")
    draw.line([(52, 47), (53, 48), (54, 49), (54, 51), (53, 52), (52, 53)], fill="white")

    if utc.microsecond < 500_000:
        draw.polygon(
            [(63, 54), (77, 50), (74, 54), (85, 54),
             (85, 52), (90, 56), (85, 60), (85, 58),
             (70, 61), (73, 56), (63, 56)],
            fill="white",
        )

    draw.line((102, 51, 115, 45), fill="white")
    draw.rounded_rectangle((98, 51, 127, 62), radius=2, outline="white")
    for y in (54, 56, 58):
        draw.line((101, y, 108, y), fill="white")
    draw.ellipse((114, 53, 122, 60), outline="white")
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
    alert = SyncAlert()
    alert_image = render_sync_alert()
    threading.Thread(target=monitor_ntp, args=(alert,), daemon=True).start()

    while True:
        now = datetime.now(timezone.utc)
        with canvas(device) as draw:
            image = alert_image if alert.visible(time.monotonic()) else render_clock(now)
            draw.bitmap((0, 0), image, fill="white")
        time.sleep(0.1)


if __name__ == "__main__":
    main()
