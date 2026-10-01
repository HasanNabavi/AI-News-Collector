from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import json
import jdatetime

from B0_NewsCollector import collect_news
from C0_FilterLinkEquivalency import filter_link_equivalency
from D0_FilterTittleEquivalency import filter_title_equivalency


def get_next_run_number():
    """
    Get the next real pipeline run number.

    The number is increased at the start of every run,
    including runs that later fail.
    """

    with open(
        "A2_RunCounter.json",
        "r",
        encoding="utf-8"
    ) as file:
        counter_data = json.load(file)

    last_run_number = counter_data.get(
        "last_run_number",
        0
    )

    next_run_number = last_run_number + 1

    counter_data["last_run_number"] = next_run_number

    with open(
        "A2_RunCounter.json",
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            counter_data,
            file,
            ensure_ascii=False,
            indent=2
        )

    return next_run_number


def update_run_state(
    run_number,
    run_reference_time
):
    """
    Add the successful run to A1_RunState.json.

    A1 keeps only the latest 100 successful runs.
    """

    try:
        with open(
            "A1_RunState.json",
            "r",
            encoding="utf-8"
        ) as file:
            state_data = json.load(file)

    except (
        FileNotFoundError,
        json.JSONDecodeError
    ):
        state_data = {
            "runs": []
        }

    # Support old A1 format during migration
    old_last_run = state_data.get(
        "last_successful_run"
    )

    if old_last_run:
        if isinstance(old_last_run, dict):
            old_timestamp = old_last_run.get(
                "timestamp_utc",
                ""
            )
            old_iran = old_last_run.get(
                "iran",
                ""
            )
            old_gregorian = old_last_run.get(
                "gregorian_utc",
                ""
            )

        else:
            old_timestamp = old_last_run
            old_iran = ""
            old_gregorian = ""

        if old_timestamp:
            if "runs" not in state_data:
                state_data["runs"] = []

            # Preserve the old successful run.
            # Run number is unknown because the old format
            # did not store it.
            state_data["runs"].append({
                "run_number": 0,
                "timestamp_utc": old_timestamp,
                "iran": old_iran,
                "gregorian_utc": old_gregorian
            })

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

    new_run = {
        "run_number": run_number,
        "timestamp_utc": run_reference_time,
        "iran": iran_date_time,
        "gregorian_utc": gregorian_utc
    }

    runs = state_data.get(
        "runs",
        []
    )

    runs.insert(
        0,
        new_run
    )

    # Keep only the latest 100 successful runs
    runs = runs[:100]

    state_data = {
        "runs": runs
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
    # Capture the real run number at the beginning.
    run_number = get_next_run_number()

    # Capture the reference time at the beginning.
    run_reference_time = datetime.now(
        timezone.utc
    ).isoformat()

    print("AI & Robotics News Pipeline")
    print("=" * 40)

    print(
        f"Run number: {run_number}"
    )

    print(
        f"Run reference time: "
        f"{run_reference_time}"
    )

    print("\n[1/3] Collecting news...")
    collect_news()

    print(
        "\n[2/3] Filtering link equivalency..."
    )
    filter_link_equivalency()

    print(
        "\n[3/3] Filtering title equivalency..."
    )
    filter_title_equivalency()

    # MUST REMAIN THE FINAL STEP.
    # A1 is updated only after the entire pipeline succeeds.
    update_run_state(
        run_number,
        run_reference_time
    )

    print(
        "\nPipeline completed successfully."
    )


if __name__ == "__main__":
    main()
