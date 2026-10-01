from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import json
import jdatetime

from B0_NewsCollector import collect_news
from C0_FilterLinkEquivalency import filter_link_equivalency
from D0_FilterTittleEquivalency import filter_title_equivalency


def update_run_state(run_reference_time):
    # Convert UTC reference time to datetime
    utc_datetime = datetime.fromisoformat(
        run_reference_time
    )

    # Iran time
    iran_datetime = utc_datetime.astimezone(
        ZoneInfo("Asia/Tehran")
    )

    # Convert Gregorian date to Persian date
    iran_jalali = jdatetime.datetime.fromgregorian(
        datetime=iran_datetime
    )

    iran_date_time = (
        f"{iran_jalali.year:04d}-"
        f"{iran_jalali.month:02d}-"
        f"{iran_jalali.day:02d} -- "
        f"{iran_jalali.hour:02d}-"
        f"{iran_jalali.minute:02d}-"
        f"{iran_jalali.second:02d}"
    )

    # Gregorian UTC display
    gregorian_utc = (
        f"{utc_datetime.year:04d}-"
        f"{utc_datetime.month:02d}-"
        f"{utc_datetime.day:02d} -- "
        f"{utc_datetime.hour:02d}-"
        f"{utc_datetime.minute:02d}-"
        f"{utc_datetime.second:02d}"
    )

    state_data = {
        "last_successful_run": {
            "timestamp_utc": run_reference_time,
            "iran": iran_date_time,
            "gregorian_utc": gregorian_utc
        }
    }

    with open(
        "A1_RunState.json",
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            state_data,
            file,
            ensure_ascii=False,
            indent=2
        )


def main():
    # Capture the start time of this pipeline run.
    # This value is saved to A1 only after the entire pipeline succeeds.
    run_reference_time = datetime.now(timezone.utc).isoformat()

    print("AI & Robotics News Pipeline")
    print("=" * 40)

    print(f"Run reference time: {run_reference_time}")

    print("\n[1/3] Collecting news...")
    collect_news()

    print("\n[2/3] Filtering link equivalency...")
    filter_link_equivalency()

    print("\n[3/3] Filtering title equivalency...")
    filter_title_equivalency()

    # MUST REMAIN THE FINAL STEP IN A0
    update_run_state(run_reference_time)

    print("\nPipeline completed successfully.")


if __name__ == "__main__":
    main()
