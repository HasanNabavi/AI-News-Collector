import json
import re


def title_similarity(title1, title2):
    stop_words = {
        "the", "a", "an", "and", "or", "of", "to", "in", "on",
        "for", "with", "from", "new", "ai", "artificial",
        "intelligence", "robot", "robots", "robotics"
    }

    words1 = {
        word
        for word in re.findall(r"\w+", title1.lower())
        if word not in stop_words
    }

    words2 = {
        word
        for word in re.findall(r"\w+", title2.lower())
        if word not in stop_words
    }

    if not words1 or not words2:
        return 0

    intersection = words1 & words2
    union = words1 | words2

    return len(intersection) / len(union)


def filter_title_equivalency():
    with open(
        "C1_NewsAfterLinkEquivalencyRun.json",
        "r",
        encoding="utf-8"
    ) as file:
        news_data = json.load(file)

    news = news_data.get("news", [])

    processed_news = []

    for item in news:
        title = item.get("title", "")

        max_score = 0

        for old_item in processed_news:
            old_title = old_item.get("title", "")

            score = title_similarity(title, old_title)

            if score > max_score:
                max_score = score

        if max_score >= 0.50:
            status = "Suspicious"
        else:
            status = "Non-similar"

        new_item = item.copy()
        new_item["title_similarity_score"] = round(max_score, 4)
        new_item["title_similarity_status"] = status

        processed_news.append(new_item)

    with open(
        "D1_NewsAfterTittleEquivalencyRun.json",
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            {"news": processed_news},
            file,
            ensure_ascii=False,
            indent=2
        )

    print(f"Input news: {len(news)}")
    print(f"Output news: {len(processed_news)}")


if __name__ == "__main__":
    filter_title_equivalency()
