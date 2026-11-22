#!/usr/bin/env python3
#
# SSD1309 SPI OLED clock
# License: GPLv3, see: www.gnu.org/licenses/gpl-3.0.html

import logging
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
SYNC_NOTIFICATION = Path("/run/raspiwwv-rtc-synced")

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

LOCAL_FONT = {
    " ": ("0",) * 7,
    "-": ("000", "000", "000", "111", "000", "000", "000"),
    ":": ("0", "0", "1", "0", "1", "0", "0"),
    "0": ("0110", "1001", "1001", "1001", "1001", "1001", "0110"),
    "1": ("0100", "1100", "0100", "0100", "0100", "0100", "1110"),
    "2": ("1110", "0001", "0001", "0110", "1000", "1000", "1111"),
    "3": ("1110", "0001", "0001", "0110", "0001", "0001", "1110"),
    "4": ("1001", "1001", "1001", "1111", "0001", "0001", "0001"),
    "5": ("1111", "1000", "1000", "1110", "0001", "0001", "1110"),
    "6": ("0111", "1000", "1000", "1110", "1001", "1001", "0110"),
    "7": ("1111", "0001", "0010", "0010", "0100", "0100", "0100"),
    "8": ("0110", "1001", "1001", "0110", "1001", "1001", "0110"),
    "9": ("0110", "1001", "1001", "0111", "0001", "0001", "1110"),
    "A": ("0110", "1001", "1001", "1111", "1001", "1001", "1001"),
    "C": ("0111", "1000", "1000", "1000", "1000", "1000", "0111"),
    "E": ("1111", "1000", "1000", "1110", "1000", "1000", "1111"),
    "I": ("1",) * 7,
    "M": ("1001", "1111", "1111", "1001", "1001", "1001", "1001"),
    "O": ("0110", "1001", "1001", "1001", "1001", "1001", "0110"),
    "T": ("1111", "0110", "0110", "0110", "0110", "0110", "0110"),
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


def monitor_rtc_sync(alert):
    last_error = None
    while True:
        try:
            SYNC_NOTIFICATION.stat()
            synchronized = True
        except FileNotFoundError:
            synchronized = False
        except OSError as error:
            detail = str(error)
            if detail != last_error:
                logging.warning("Cannot check RTC synchronization notification: %s", detail)
                last_error = detail
            time.sleep(SYNC_POLL_SECONDS)
            continue
        if last_error is not None:
            logging.info("RTC synchronization notification checks resumed")
            last_error = None
        alert.update(synchronized, time.monotonic())
        time.sleep(SYNC_POLL_SECONDS)


def render_sync_alert():
    image = Image.new("1", (128, 64), 0)
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(str(Path(__file__).parent / "fonts" / "VCR_font.ttf"), 20)
    draw.rectangle((0, 0, 127, 63), outline="white")
    for text, y in (("RTC", 7), ("SYNCED", 35)):
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


def local_text_width(text):
    return sum(len(LOCAL_FONT[char][0]) + 1 for char in text) - 1


def draw_local_text(draw, text, x, y):
    for char in text:
        glyph = LOCAL_FONT[char]
        for row, pixels in enumerate(glyph):
            for col, pixel in enumerate(pixels):
                if pixel == "1":
                    draw.point((x + col, y + row), fill="white")
        x += len(glyph[0]) + 1


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
    draw_local_text(draw, california, 0, 1)
    draw_local_text(draw, colorado, 128 - local_text_width(colorado), 1)

    utc = now.astimezone(timezone.utc)
    draw_small_text(draw, "UTC:", 3, 25)
    draw_led_time(draw, utc.strftime("%H:%M:%S"), 25, 15)
    date = utc.strftime("%Y-%m-%d")
    draw_local_text(draw, date, 0, 51)

    draw.line((60, 49, 60, 61), fill="white")
    draw.line((57, 62, 63, 62), fill="white")
    draw.line([(56, 45), (54, 48), (54, 52), (56, 55)], fill="white")
    draw.line([(58, 47), (57, 49), (57, 51), (58, 53)], fill="white")
    draw.line([(64, 45), (66, 48), (66, 52), (64, 55)], fill="white")
    draw.line([(62, 47), (63, 49), (63, 51), (62, 53)], fill="white")

    if utc.microsecond < 500_000:
        draw.polygon(
            [(70, 54), (82, 50), (79, 54), (88, 54),
             (88, 52), (92, 56), (88, 60), (88, 58),
             (76, 61), (78, 56), (70, 56)],
            fill="white",
        )

    draw.line((105, 51, 117, 45), fill="white")
    draw.rounded_rectangle((101, 51, 127, 62), radius=2, outline="white")
    for y in (54, 56, 58):
        draw.line((104, y, 110, y), fill="white")
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
    threading.Thread(target=monitor_rtc_sync, args=(alert,), daemon=True).start()

    while True:
        now = datetime.now(timezone.utc)
        with canvas(device) as draw:
            image = alert_image if alert.visible(time.monotonic()) else render_clock(now)
            draw.bitmap((0, 0), image, fill="white")
        time.sleep(0.1)


if __name__ == "__main__":
    main()
