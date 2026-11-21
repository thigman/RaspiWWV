import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from PIL import ImageChops

import clockOLED


class ClockOLEDTests(unittest.TestCase):
    def test_render_clock_has_128_by_64_monochrome_artwork(self):
        image = clockOLED.render_clock(
            datetime(2026, 1, 1, 12, 34, 56, tzinfo=timezone.utc)
        )
        self.assertEqual(image.size, (128, 64))
        self.assertEqual(image.mode, "1")

    def test_local_times_follow_daylight_saving(self):
        cases = [
            (datetime(2026, 1, 1, 12, 34, tzinfo=timezone.utc),
             "CO TIME: 05:34", "CA TIME: 04:34"),
            (datetime(2026, 7, 1, 12, 34, tzinfo=timezone.utc),
             "CO TIME: 06:34", "CA TIME: 05:34"),
            (datetime(2026, 3, 8, 9, 59, tzinfo=timezone.utc),
             "CO TIME: 03:59", "CA TIME: 01:59"),
            (datetime(2026, 3, 8, 10, 0, tzinfo=timezone.utc),
             "CO TIME: 04:00", "CA TIME: 03:00"),
        ]
        for now, colorado, california in cases:
            with self.subTest(now=now), patch.object(
                clockOLED, "draw_small_text", wraps=clockOLED.draw_small_text
            ) as draw_text:
                clockOLED.render_clock(now)
                calls = draw_text.call_args_list
                self.assertEqual(calls[0].args[1:4], (colorado, 0, 2))
                self.assertEqual(calls[1].args[1:4], (california, 73, 2))
                self.assertEqual(calls[2].args[1], "UTC:")

    def test_clock_and_date_are_utc(self):
        local_time = datetime(
            2025, 12, 31, 16, 34, 56, tzinfo=timezone(timedelta(hours=-8))
        )
        with patch.object(clockOLED, "draw_led_time", wraps=clockOLED.draw_led_time) as led, \
             patch.object(clockOLED, "draw_small_text", wraps=clockOLED.draw_small_text) as draw_text:
            clockOLED.render_clock(local_time)
        self.assertEqual(led.call_args.args[1], "00:34:56")
        self.assertEqual(draw_text.call_args_list[-1].args[1:4], ("2026-01-01", 0, 52))

    def test_utc_digits_update_with_seconds(self):
        first = clockOLED.render_clock(
            datetime(2026, 1, 1, 12, 34, 56, tzinfo=timezone.utc)
        )
        second = clockOLED.render_clock(
            datetime(2026, 1, 1, 12, 34, 57, tzinfo=timezone.utc)
        )
        self.assertIsNotNone(ImageChops.difference(
            first.crop((25, 18, 128, 43)), second.crop((25, 18, 128, 43))
        ).getbbox())

    def test_bolt_flashes_each_second_without_changing_other_art(self):
        now = datetime(2026, 1, 1, 12, 34, 56, tzinfo=timezone.utc)
        on = clockOLED.render_clock(now)
        off = clockOLED.render_clock(now.replace(microsecond=500_000))
        next_on = clockOLED.render_clock(now + timedelta(seconds=1))
        bolt = (60, 45, 94, 63)
        self.assertIsNotNone(on.crop(bolt).getbbox())
        self.assertIsNone(off.crop(bolt).getbbox())
        self.assertEqual(on.crop(bolt).tobytes(), next_on.crop(bolt).tobytes())
        for box in ((0, 52, 39, 57), (42, 45, 57, 63), (98, 45, 128, 63)):
            self.assertIsNotNone(on.crop(box).getbbox())
            self.assertEqual(on.crop(box).tobytes(), off.crop(box).tobytes())


if __name__ == "__main__":
    unittest.main()
