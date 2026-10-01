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

    The run number is increased at the beginning of every
    pipeline execution, including executions that later fail.
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
    Save the successful pipeline run in A1.

    A1 keeps only the latest 100 successful runs.

    If A1 still contains the old format, its old timestamp
    is NOT converted into a fake run number.
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
        state_data = {}

    # --------------------------------------------------
    # Read existing run history
    # --------------------------------------------------

    runs = state_data.get(
        "runs",
        []
    )

    # --------------------------------------------------
    # If the old A1 format still exists, do NOT migrate
    # it into the new run history.
    #
    # The old timestamp has already been used by B0
    # during this run. From this successful run onward,
    # A1 will use the new format.
    # --------------------------------------------------

    new_run = {
        "run_number": run_number,
        "timestamp_utc": run_reference_time,
        "iran": "",
        "gregorian_utc": ""
    }

    # --------------------------------------------------
    # Convert UTC reference time to datetime
    # --------------------------------------------------

    utc_datetime = datetime.fromisoformat(
        run_reference_time
    )

    # --------------------------------------------------
    # Iran local time
    # --------------------------------------------------

    iran_datetime = utc_datetime.astimezone(
        ZoneInfo("Asia/Tehran")
    )

    # Convert Gregorian date to Persian date
    iran_jalali = jdatetime.datetime.fromgregorian(
        datetime=iran_datetime
    )

    new_run["iran"] = (
        f"{iran_jalali.year:04d}-"
        f"{iran_jalali.month:02d}-"
        f"{iran_jalali.day:02d} -- "
        f"{iran_jalali.hour:02d}-"
        f"{iran_jalali.minute:02d}-"
        f"{iran_jalali.second:02d}"
    )

    # --------------------------------------------------
    # Gregorian UTC display
    # --------------------------------------------------

    new_run["gregorian_utc"] = (
        f"{utc_datetime.year:04d}-"
        f"{utc_datetime.month:02d}-"
        f"{utc_datetime.day:02d} -- "
        f"{utc_datetime.hour:02d}-"
        f"{utc_datetime.minute:02d}-"
        f"{utc_datetime.second:02d}"
    )

    # --------------------------------------------------
    # Add the new successful run to the beginning
    # --------------------------------------------------

    runs.insert(
        0,
        new_run
    )

    # --------------------------------------------------
    # Keep only the latest 100 successful runs
    # --------------------------------------------------

    runs = runs[:100]

    state_data = {
        "runs": runs
    }

    # --------------------------------------------------
    # Save A1
    # --------------------------------------------------

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
    # --------------------------------------------------
    # Generate the real run number at the beginning.
    #
    # This happens before any pipeline stage.
    # Therefore, even a failed run consumes its number.
    # --------------------------------------------------

    run_number = get_next_run_number()

    # --------------------------------------------------
    # Capture the run reference time at the beginning.
    #
    # This timestamp is saved to A1 only if the entire
    # pipeline succeeds.
    # --------------------------------------------------

    run_reference_time = datetime.now(
        timezone.utc
    ).isoformat()

    print(
        "AI & Robotics News Pipeline"
    )
    print(
        "=" * 40
    )

    print(
        f"Run number: {run_number}"
    )

    print(
        f"Run reference time: "
        f"{run_reference_time}"
    )

    # --------------------------------------------------
    # Pipeline stages
    # --------------------------------------------------

    print(
        "\n[1/3] Collecting news..."
    )

    collect_news()

    print(
        "\n[2/3] Filtering link equivalency..."
    )

    filter_link_equivalency()

    print(
        "\n[3/3] Filtering title equivalency..."
    )

    filter_title_equivalency()

    # --------------------------------------------------
    # MUST REMAIN THE FINAL STEP
    #
    # A1 is updated only after every previous stage
    # has completed successfully.
    # --------------------------------------------------

    update_run_state(
        run_number,
        run_reference_time
    )

    print(
        "\nPipeline completed successfully."
    )


if __name__ == "__main__":
    main()
