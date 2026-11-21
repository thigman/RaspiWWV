import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from PIL import Image

import clockOLED


class ClockOLEDTests(unittest.TestCase):
    def test_render_clock_has_128_by_64_monochrome_artwork(self):
        image = clockOLED.render_clock(
            datetime(2026, 1, 1, 12, 34, 56, tzinfo=timezone.utc)
        )
        self.assertIsInstance(image, Image.Image)
        self.assertEqual(image.size, (128, 64))
        self.assertEqual(image.mode, "1")

    def test_bolt_blinks_once_per_second(self):
        even = clockOLED.render_clock(
            datetime(2026, 1, 1, 12, 34, 56, tzinfo=timezone.utc)
        )
        odd = clockOLED.render_clock(
            datetime(2026, 1, 1, 12, 34, 57, tzinfo=timezone.utc)
        )
        self.assertNotEqual(
            even.crop((89, 49, 104, 63)).tobytes(),
            odd.crop((89, 49, 104, 63)).tobytes(),
        )

    def test_middle_box_displays_utc_time_with_seconds(self):
        local_time = datetime(
            2026, 1, 1, 4, 34, 56, tzinfo=timezone(timedelta(hours=-8))
        )
        with patch.object(
            clockOLED, "draw_centered_text", wraps=clockOLED.draw_centered_text
        ) as draw_centered:
            clockOLED.render_clock(local_time)
        self.assertEqual(draw_centered.call_args_list[0].args[2], "UTC: 12:34:56")

    def test_middle_box_changes_each_second(self):
        first = clockOLED.render_clock(
            datetime(2026, 1, 1, 12, 34, 56, tzinfo=timezone.utc)
        )
        second = clockOLED.render_clock(
            datetime(2026, 1, 1, 12, 34, 57, tzinfo=timezone.utc)
        )
        self.assertNotEqual(
            first.crop((2, 16, 126, 47)).tobytes(),
            second.crop((2, 16, 126, 47)).tobytes(),
        )

    def test_prefixed_time_fits_inside_middle_box(self):
        font = clockOLED.ImageFont.truetype(clockOLED.VCR_FONT, 14)
        for hour in range(24):
            for minute in range(60):
                text = f"UTC: {hour:02}:{minute:02}:59"
                bbox = font.getbbox(text)
                self.assertLessEqual(bbox[2] - bbox[0], 123, text)

    def test_transmitter_art_shows_tower_and_signal(self):
        image = clockOLED.render_clock(
            datetime(2026, 1, 1, 12, 34, 56, tzinfo=timezone.utc)
        )
        self.assertTrue(image.getpixel((10, 50)))
        self.assertTrue(image.getpixel((6, 61)))
        self.assertTrue(image.getpixel((14, 61)))
        self.assertTrue(image.getpixel((3, 50)))
        self.assertTrue(image.getpixel((17, 50)))


if __name__ == "__main__":
    unittest.main()
