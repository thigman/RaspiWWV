#!/usr/bin/env python3
"""Write synchronized system time to the hardware RTC."""

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

RTC = Path("/dev/rtc0")
EARLIEST_TIME = datetime(2024, 1, 1, tzinfo=timezone.utc)
LATEST_TIME = datetime(2100, 1, 1, tzinfo=timezone.utc)


def main():
    if not RTC.exists():
        print(f"{RTC} is missing; leaving the RTC unchanged.")
        return 0

    try:
        status = subprocess.run(
            ["timedatectl", "show", "--property=NTPSynchronized", "--value"],
            check=True, capture_output=True, text=True, timeout=15,
        ).stdout.strip()
    except subprocess.CalledProcessError as error:
        detail = error.stderr.strip() if error.stderr else str(error)
        print(f"Cannot determine time synchronization status: {detail}", file=sys.stderr)
        return 1
    except (OSError, subprocess.TimeoutExpired) as error:
        print(f"Cannot determine time synchronization status: {error}", file=sys.stderr)
        return 1

    if status == "no":
        print("System time is not synchronized; leaving the RTC unchanged.")
        return 0
    if status != "yes":
        print(f"Unexpected time synchronization status {status!r}; leaving the RTC unchanged.",
              file=sys.stderr)
        return 1

    now = datetime.now(timezone.utc)
    if not EARLIEST_TIME <= now < LATEST_TIME:
        print(f"System time {now.isoformat()} is outside the safe RTC range; "
              "leaving the RTC unchanged.", file=sys.stderr)
        return 1

    try:
        subprocess.run(["hwclock", "-w", "-f", str(RTC)], check=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as error:
        print(f"Failed to write {RTC}: {error}", file=sys.stderr)
        return 1
    print(f"Updated {RTC} from synchronized system time ({now.isoformat()}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
