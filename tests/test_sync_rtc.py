import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import sync_rtc


class RTCSyncTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.notification = Path(temp.name) / "rtc-synced"
        marker = patch.object(sync_rtc, "SYNC_NOTIFICATION", self.notification)
        marker.start()
        self.addCleanup(marker.stop)

    def run_sync(self, status="yes", now=None, exists=True, write_error=None):
        clock = Mock()
        clock.now.return_value = now or datetime(2026, 1, 1, tzinfo=timezone.utc)
        responses = [
            subprocess.CompletedProcess([], 0, stdout=status),
            write_error or subprocess.CompletedProcess([], 0),
        ]
        with patch.object(sync_rtc.RTC.__class__, "exists", return_value=exists), \
             patch.object(sync_rtc, "datetime", clock), \
             patch.object(sync_rtc.subprocess, "run", side_effect=responses) as run:
            result = sync_rtc.main()
        return result, run

    def test_synchronized_time_is_written_to_rtc(self):
        result, run = self.run_sync()
        self.assertEqual(result, 0)
        self.assertEqual(run.call_args_list[0].args[0],
                         ["timedatectl", "show", "--property=NTPSynchronized", "--value"])
        self.assertEqual(run.call_args_list[1].args[0], ["hwclock", "-w", "-f", "/dev/rtc0"])
        self.assertTrue(self.notification.exists())
        self.assertEqual(self.run_sync()[1].call_count, 2)

    def test_unsynchronized_or_unknown_status_never_writes(self):
        for status in ("no", "", "unexpected"):
            with self.subTest(status=status):
                result, run = self.run_sync(status=status)
                self.assertEqual(result, 0 if status == "no" else 1)
                self.assertEqual(run.call_count, 1)
                self.assertFalse(self.notification.exists())

    def test_missing_rtc_skips_all_commands(self):
        result, run = self.run_sync(exists=False)
        self.assertEqual(result, 0)
        run.assert_not_called()
        self.assertFalse(self.notification.exists())

    def test_implausible_dates_never_write(self):
        for now in (datetime(2023, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
                    datetime(2100, 1, 1, tzinfo=timezone.utc)):
            with self.subTest(now=now):
                result, run = self.run_sync(now=now)
                self.assertEqual(result, 1)
                self.assertEqual(run.call_count, 1)

    def test_safe_date_range_includes_both_supported_endpoints(self):
        for now in (datetime(2024, 1, 1, tzinfo=timezone.utc),
                    datetime(2099, 12, 31, 23, 59, 59, tzinfo=timezone.utc)):
            with self.subTest(now=now):
                result, run = self.run_sync(now=now)
                self.assertEqual(result, 0)
                self.assertEqual(run.call_count, 2)

    def test_status_command_failure_never_writes(self):
        for error in (OSError("missing timedatectl"),
                      subprocess.CalledProcessError(1, "timedatectl"),
                      subprocess.TimeoutExpired("timedatectl", 15)):
            with self.subTest(error=error), \
                 patch.object(sync_rtc.RTC.__class__, "exists", return_value=True), \
                 patch.object(sync_rtc.subprocess, "run", side_effect=error) as run:
                self.assertEqual(sync_rtc.main(), 1)
                self.assertEqual(run.call_count, 1)

    def test_hwclock_failure_is_reported(self):
        result, run = self.run_sync(
            write_error=subprocess.CalledProcessError(1, "hwclock")
        )
        self.assertEqual(result, 1)
        self.assertEqual(run.call_count, 2)
        self.assertFalse(self.notification.exists())

    def test_notification_failure_is_reported_after_successful_write(self):
        self.notification = self.notification / "missing" / "rtc-synced"
        with patch.object(sync_rtc, "SYNC_NOTIFICATION", self.notification):
            result, run = self.run_sync()
        self.assertEqual(result, 1)
        self.assertEqual(run.call_count, 2)


if __name__ == "__main__":
    unittest.main()
