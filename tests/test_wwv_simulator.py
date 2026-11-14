import subprocess
import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import wwv_simulator as wwv


class AnnouncementTests(unittest.TestCase):
    def test_round_minute_has_no_directory_argument(self):
        names = [path.name for path in wwv.announcement(
            datetime(2026, 1, 1, 12, 29, tzinfo=timezone.utc)
        )]
        self.assertEqual(names, [
            "wwv_at_the_tone.mp3", "12.mp3", "hours.mp3", "30.mp3",
            "minutes.mp3", "wwv_utc.mp3",
        ])

    def test_midnight_and_compound_numbers(self):
        midnight = wwv.announcement(datetime(2026, 1, 1, 23, 59, tzinfo=timezone.utc))
        compound = wwv.announcement(datetime(2026, 1, 1, 21, 21, tzinfo=timezone.utc))
        self.assertEqual([p.name for p in midnight][1:5],
                         ["0.mp3", "hours.mp3", "0.mp3", "minutes.mp3"])
        self.assertEqual([p.name for p in compound][1:7],
                         ["20.mp3", "1.mp3", "hours.mp3", "20.mp3",
                          "2.mp3", "minutes.mp3"])


class RecoveryTests(unittest.TestCase):
    def run_loop(self, times, player, monotonic_values, run_effect=None):
        clock = Mock()
        clock.now.side_effect = times
        with patch.object(wwv, "datetime", clock), \
             patch.object(wwv.time, "monotonic", side_effect=monotonic_values), \
             patch.object(wwv.time, "sleep"), \
             patch.object(wwv.subprocess, "Popen", return_value=player), \
             patch.object(wwv.subprocess, "run", side_effect=run_effect) as run:
            try:
                wwv.main()
            finally:
                self.run_mock = run

    def test_early_player_exit_is_a_failure(self):
        player = Mock()
        player.poll.side_effect = [1, 1]
        with self.assertRaisesRegex(RuntimeError, "aplay exited"):
            self.run_loop([datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                           datetime(2026, 1, 1, 12, 0, 1, tzinfo=timezone.utc)],
                          player, [0, 1])

    def test_hung_player_is_terminated(self):
        player = Mock()
        player.poll.return_value = None
        with self.assertRaisesRegex(RuntimeError, "within 65 seconds"):
            self.run_loop([datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                           datetime(2026, 1, 1, 12, 1, 6, tzinfo=timezone.utc)],
                          player, [0, 66])
        player.terminate.assert_called_once()

    def test_announcement_failure_propagates_and_stops_player(self):
        player = Mock()
        player.poll.return_value = None
        with self.assertRaises(subprocess.TimeoutExpired):
            self.run_loop([datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                           datetime(2026, 1, 1, 12, 0, 45, tzinfo=timezone.utc)],
                          player, [0, 45],
                          subprocess.TimeoutExpired("mpg123", 25))
        player.terminate.assert_called_once()
        self.assertEqual(self.run_mock.call_args.kwargs, {"check": True, "timeout": 25})

    def test_announcement_plays_once_in_the_started_minute(self):
        player = Mock()
        player.poll.return_value = None
        times = [
            datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 1, 1, 12, 0, 45, tzinfo=timezone.utc),
            datetime(2026, 1, 1, 12, 0, 46, tzinfo=timezone.utc),
        ]
        with self.assertRaises(StopIteration):
            self.run_loop(times, player, [0, 45, 46])
        self.run_mock.assert_called_once()
        self.assertEqual(self.run_mock.call_args.args[0][:2], ["mpg123", "-q"])
        player.terminate.assert_called_once()


if __name__ == "__main__":
    unittest.main()
