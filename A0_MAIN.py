from datetime import datetime, timezone
import json

from B0_NewsCollector import collect_news
from C0_FilterLinkEquivalency import filter_link_equivalency
from D0_FilterTittleEquivalency import filter_title_equivalency


def update_run_state(run_reference_time):
    with open("A1_RunState.json", "w", encoding="utf-8") as file:
        json.dump(
            {"last_successful_run": run_reference_time},
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
