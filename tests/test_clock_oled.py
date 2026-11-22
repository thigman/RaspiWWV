import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
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
                clockOLED, "draw_local_text", wraps=clockOLED.draw_local_text
            ) as draw_text:
                clockOLED.render_clock(now)
                calls = draw_text.call_args_list
                self.assertEqual(calls[0].args[1:4], (colorado, 0, 1))
                self.assertEqual(calls[1].args[1:4],
                                 (california, 128 - clockOLED.local_text_width(california), 1))

    def test_clock_and_date_are_utc(self):
        local_time = datetime(
            2025, 12, 31, 16, 34, 56, tzinfo=timezone(timedelta(hours=-8))
        )
        with patch.object(clockOLED, "draw_led_time", wraps=clockOLED.draw_led_time) as led, \
             patch.object(clockOLED, "draw_small_text", wraps=clockOLED.draw_small_text) as draw_text:
            clockOLED.render_clock(local_time)
        self.assertEqual(led.call_args.args[1], "00:34:56")
        self.assertEqual(led.call_args.args[2:4], (25, 15))
        self.assertEqual(draw_text.call_args_list[-1].args[1:4], ("2026-01-01", 0, 52))

    def test_local_time_lines_fit_without_overlap(self):
        for hour in range(24):
            for minute in range(60):
                colorado = f"CO TIME: {hour:02}:{minute:02}"
                california = f"CA TIME: {hour:02}:{minute:02}"
                self.assertLessEqual(clockOLED.local_text_width(colorado)
                                     + clockOLED.local_text_width(california), 127)

    def test_larger_local_times_and_space_below_utc(self):
        image = clockOLED.render_clock(
            datetime(2026, 1, 1, 12, 34, 56, tzinfo=timezone.utc)
        )
        self.assertEqual(image.crop((0, 0, 64, 10)).getbbox()[1::2], (1, 8))
        self.assertEqual(image.crop((64, 0, 128, 10)).getbbox()[1::2], (1, 8))
        self.assertIsNone(image.crop((0, 40, 128, 45)).getbbox())

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
        self.assertEqual(ImageChops.difference(on, off).getbbox(), (63, 50, 91, 62))
        self.assertEqual(on.crop(bolt).tobytes(), next_on.crop(bolt).tobytes())
        for box in ((0, 52, 39, 57), (42, 45, 57, 63), (98, 45, 128, 63)):
            self.assertIsNotNone(on.crop(box).getbbox())
            self.assertEqual(on.crop(box).tobytes(), off.crop(box).tobytes())

    def test_antenna_has_mast_and_separate_signal_waves(self):
        image = clockOLED.render_clock(
            datetime(2026, 1, 1, 12, 34, 56, tzinfo=timezone.utc)
        )
        for x in (41, 44, 49, 54, 57):
            self.assertTrue(image.getpixel((x, 50)))
        for x in (42, 45, 48, 50, 53, 56):
            self.assertFalse(image.getpixel((x, 50)))
        self.assertTrue(all(image.getpixel((49, y)) for y in range(49, 63)))


class RTCSyncAlertTests(unittest.TestCase):
    def test_alert_lasts_15_seconds_and_only_repeats_after_sync_loss(self):
        alert = clockOLED.SyncAlert()
        alert.update(False, 10)
        self.assertFalse(alert.visible(10))
        alert.update(True, 20)
        self.assertTrue(alert.visible(20))
        self.assertTrue(alert.visible(34.999))
        alert.update(True, 34)
        self.assertFalse(alert.visible(35))
        alert.update(False, 40)
        alert.update(True, 45)
        self.assertTrue(alert.visible(45))
        self.assertFalse(alert.visible(60))

    def test_already_synchronized_at_startup_shows_alert(self):
        alert = clockOLED.SyncAlert()
        alert.update(True, 100)
        self.assertTrue(alert.visible(100))
        self.assertFalse(alert.visible(115))

    def test_monitor_detects_rtc_write_and_does_not_repeat(self):
        alert = clockOLED.SyncAlert()
        with tempfile.TemporaryDirectory() as temp:
            marker = Path(temp) / "rtc-synced"
            calls = 0

            def sleep(_):
                nonlocal calls
                calls += 1
                if calls == 1:
                    self.assertFalse(alert.visible(10))
                    marker.touch()
                elif calls == 2:
                    self.assertTrue(alert.visible(20))
                else:
                    raise StopIteration

            with patch.object(clockOLED, "SYNC_NOTIFICATION", marker), \
                 patch.object(clockOLED.time, "monotonic", side_effect=[10, 20, 40]), \
                 patch.object(clockOLED.time, "sleep", side_effect=sleep):
                with self.assertRaises(StopIteration):
                    clockOLED.monitor_rtc_sync(alert)
        self.assertFalse(alert.visible(40))

    def test_monitor_logs_errors_and_resumes_without_false_alerts(self):
        alert = clockOLED.SyncAlert()
        with patch.object(clockOLED.SYNC_NOTIFICATION.__class__, "stat",
                          side_effect=[None, PermissionError("denied"), None]), \
             patch.object(clockOLED.time, "monotonic", side_effect=[10, 30]), \
             patch.object(clockOLED.time, "sleep",
                          side_effect=[None, None, StopIteration]), \
             self.assertLogs(level="WARNING"):
            with self.assertRaises(StopIteration):
                clockOLED.monitor_rtc_sync(alert)
        self.assertFalse(alert.visible(30))

    def test_alert_screen_is_drawn_for_oled(self):
        image = clockOLED.render_sync_alert()
        self.assertEqual(image.size, (128, 64))
        self.assertEqual(image.mode, "1")
        self.assertIsNotNone(image.crop((1, 1, 127, 63)).getbbox())


if __name__ == "__main__":
    unittest.main()
