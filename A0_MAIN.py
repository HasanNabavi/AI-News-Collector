from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import json
import jdatetime

from B0_NewsCollector import collect_news
from C0_FilterLinkEquivalency import filter_link_equivalency
from E0_ScraperManager import scrape_manager
from F0_AIGrouping import main as run_ai_grouping
from G0_AIContentGenerator import main as run_ai_content_generation
from H0_TelegramFormatedNews import main as run_telegram_formatting
from I0_TelegramInterface import main as run_telegram_interface


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

    A1 is updated only after every pipeline stage has
    completed successfully.
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

    runs = state_data.get(
        "runs",
        []
    )

    new_run = {
        "run_number": run_number,
        "timestamp_utc": run_reference_time,
        "iran": "",
        "gregorian_utc": ""
    }

    utc_datetime = datetime.fromisoformat(
        run_reference_time
    )

    iran_datetime = utc_datetime.astimezone(
        ZoneInfo("Asia/Tehran")
    )

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

    new_run["gregorian_utc"] = (
        f"{utc_datetime.year:04d}-"
        f"{utc_datetime.month:02d}-"
        f"{utc_datetime.day:02d} -- "
        f"{utc_datetime.hour:02d}-"
        f"{utc_datetime.minute:02d}-"
        f"{utc_datetime.second:02d}"
    )

    runs.insert(
        0,
        new_run
    )

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

    # --------------------------------------------------
    # Run management
    # --------------------------------------------------
    #
    # A2 is updated at the beginning.
    # Therefore, even a failed run consumes its number.
    #
    # A1 is updated only after the complete pipeline
    # succeeds and remains the final A0 step.
    # --------------------------------------------------

    run_number = get_next_run_number()

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
    # 1. News Collector
    # --------------------------------------------------

    print(
        "\n[1/7] Collecting news..."
    )

    collect_news()

    # --------------------------------------------------
    # 2. Link Equivalency Filter
    # --------------------------------------------------

    print(
        "\n[2/7] Filtering link equivalency..."
    )

    filter_link_equivalency()

    # --------------------------------------------------
    # 3. Scraper Manager
    # --------------------------------------------------

    print(
        "\n[3/7] Scraping news..."
    )

    scrape_manager()

    # --------------------------------------------------
    # 4. AI Grouping
    # --------------------------------------------------

    print(
        "\n[4/7] Grouping news..."
    )

    run_ai_grouping()

    # --------------------------------------------------
    # 5. AI Content Generation
    # --------------------------------------------------

    print(
        "\n[5/7] Generating content..."
    )

    run_ai_content_generation()

    # --------------------------------------------------
    # 6. Telegram Formatting
    # --------------------------------------------------

    print(
        "\n[6/7] Formatting Telegram news..."
    )

    run_telegram_formatting()

    # --------------------------------------------------
    # 7. Telegram Interface
    # --------------------------------------------------

    print(
        "\n[7/7] Publishing to Telegram..."
    )

    run_telegram_interface()

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
