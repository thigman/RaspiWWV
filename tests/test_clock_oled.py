import unittest
from datetime import datetime, timezone

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
        self.assertNotEqual(even.tobytes(), odd.tobytes())


if __name__ == "__main__":
    unittest.main()
