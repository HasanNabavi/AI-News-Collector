from B0_NewsCollector import collect_news
from C0_FilterLinkEquivalency import filter_link_equivalency
from D0_FilterTittleEquivalency import filter_title_equivalency


def main():
    print("AI & Robotics News Pipeline")
    print("=" * 40)

    print("\n[1/3] Collecting news...")
    collect_news()

    print("\n[2/3] Filtering link equivalency...")
    filter_link_equivalency()

    print("\n[3/3] Filtering title equivalency...")
    filter_title_equivalency()

    print("\nPipeline completed successfully.")


if __name__ == "__main__":
    main()
