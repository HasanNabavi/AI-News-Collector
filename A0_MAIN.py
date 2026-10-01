from B0_NewsCollector import collect_news
from C0_FilterLinkEquivalency import filter_link_equivalency
from D0_FilterTittleEquivalency import filter_title_equivalency

import json
import shutil


def update_last_collected_news():
    shutil.copyfile(
        "B1_News.json",
        "B2_LastCollectedNews.json"
    )


def main():
    print("AI & Robotics News Pipeline")
    print("=" * 40)

    print("\n[1/4] Collecting news...")
    collect_news()

    print("\n[2/4] Filtering link equivalency...")
    filter_link_equivalency()

    print("\n[3/4] Filtering title equivalency...")
    filter_title_equivalency()

    print("\n[4/4] Updating last collected news...")
    update_last_collected_news()

    print("\nPipeline completed successfully.")


if __name__ == "__main__":
    main()
