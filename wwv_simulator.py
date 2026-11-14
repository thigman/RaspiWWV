#!/usr/bin/env python3
"""Play the WWV-style time signal and announce the next UTC minute."""

import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

SOUNDS = Path(__file__).resolve().parent / "sounds"


def number_sounds(number):
    if number <= 20 or number % 10 == 0:
        return [SOUNDS / f"{number}.mp3"]
    return [SOUNDS / f"{number // 10 * 10}.mp3", SOUNDS / f"{number % 10}.mp3"]


def announcement(now):
    next_minute = now + timedelta(minutes=1)
    hours, minutes = next_minute.hour, next_minute.minute
    return [
        SOUNDS / "wwv_at_the_tone.mp3",
        *number_sounds(hours),
        SOUNDS / ("hour.mp3" if hours == 1 else "hours.mp3"),
        *number_sounds(minutes),
        SOUNDS / ("minute.mp3" if minutes == 1 else "minutes.mp3"),
        SOUNDS / "wwv_utc.mp3",
    ]


def stop_player(player):
    if player is not None and player.poll() is None:
        player.terminate()
        try:
            player.wait(timeout=5)
        except subprocess.TimeoutExpired:
            player.kill()
            player.wait()


def main():
    player = None
    player_started = None
    current_minute = None
    announced = False
    print("Waiting for the next UTC minute to start audio.", flush=True)
    try:
        while True:
            now = datetime.now(timezone.utc)
            minute = now.replace(second=0, microsecond=0)

            if player is not None:
                status = player.poll()
                elapsed = time.monotonic() - player_started
                if status is not None:
                    player = None
                    if status != 0 or elapsed < 50:
                        raise RuntimeError(
                            f"aplay exited after {elapsed:.1f}s with status {status}"
                        )
                elif elapsed > 65:
                    raise RuntimeError("aplay did not finish within 65 seconds")

            if now.second == 0 and minute != current_minute:
                stop_player(player)
                player = subprocess.Popen(
                    ["aplay", "-d", "61", "-q", str(SOUNDS / "wwv-style-time-signal.wav")]
                )
                player_started = time.monotonic()
                current_minute = minute
                announced = False

            if now.second >= 45 and minute == current_minute and not announced:
                subprocess.run(
                    ["mpg123", "-q", *(str(path) for path in announcement(now))],
                    check=True,
                    timeout=25,
                )
                announced = True
            time.sleep(0.2)
    finally:
        stop_player(player)


if __name__ == "__main__":
    main()
