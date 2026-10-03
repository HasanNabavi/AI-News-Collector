import json
import numpy as np
from sentence_transformers import SentenceTransformer


# =========================
# Configuration
# =========================

INPUT_FILE = "E1_NewsAfterScrapingRun.json"
OUTPUT_FILE = "F1_NewsAfterAIGroupingRun.json"

MODEL_NAME = "BAAI/bge-small-en-v1.5"

# Initial similarity threshold.
# This value will be calibrated using real project data.
SIMILARITY_THRESHOLD = 0.75

# Maximum number of words in each text chunk.
CHUNK_SIZE = 350

# Number of words shared between consecutive chunks.
CHUNK_OVERLAP = 50


# =========================
# Load JSON
# =========================

def load_news():
    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    return data.get("news", [])


# =========================
# Text Chunking
# =========================

def chunk_text(text):
    words = text.split()

    if len(words) <= CHUNK_SIZE:
        return [text]

    chunks = []

    start = 0

    while start < len(words):
        end = start + CHUNK_SIZE
        chunk = " ".join(words[start:end])
        chunks.append(chunk)

        if end >= len(words):
            break

        start = end - CHUNK_OVERLAP

    return chunks


# =========================
# Article Embedding
# =========================

def create_article_embedding(model, text):
    chunks = chunk_text(text)

    embeddings = model.encode(
        chunks,
        normalize_embeddings=True,
        show_progress_bar=False
    )

    # Mean pooling over chunk embeddings
    article_embedding = np.mean(embeddings, axis=0)

    # Normalize final article embedding
    norm = np.linalg.norm(article_embedding)

    if norm != 0:
        article_embedding = article_embedding / norm

    return article_embedding


# =========================
# Grouping
# =========================

def group_articles(articles, embeddings):
    groups = []

    for index, embedding in enumerate(embeddings):

        assigned_group = None

        for group in groups:

            group_embedding = group["embedding"]

            similarity = float(
                np.dot(embedding, group_embedding)
            )

            if similarity >= SIMILARITY_THRESHOLD:
                assigned_group = group
                break

        if assigned_group is None:

            new_group = {
                "group_id": f"G{len(groups) + 1:04d}",
                "embedding": embedding,
                "article_indices": [index]
            }

            groups.append(new_group)

        else:

            assigned_group["article_indices"].append(index)

            # Update group centroid
            member_embeddings = [
                embeddings[i]
                for i in assigned_group["article_indices"]
            ]

            centroid = np.mean(member_embeddings, axis=0)

            norm = np.linalg.norm(centroid)

            if norm != 0:
                centroid = centroid / norm

            assigned_group["embedding"] = centroid

    return groups


# =========================
# Main
# =========================

def main():

    print("Loading news...")

    news = load_news()

    print(f"Total news: {len(news)}")

    model = SentenceTransformer(MODEL_NAME)

    valid_articles = []
    embeddings = []

    skipped_count = 0

    print("Creating article embeddings...")

    for index, article in enumerate(news):

        scraped_data = article.get("scraped_data", {})

        text = scraped_data.get("text", "")
        status = scraped_data.get("status", "")

        # Ignore unsuccessful or empty articles
        if status != "success" or not text.strip():
            skipped_count += 1
            continue

        embedding = create_article_embedding(model, text)

        valid_articles.append(article)
        embeddings.append(embedding)

        print(
            f"Embedded {len(valid_articles)} "
            f"(source index: {index})"
        )

    print()
    print(f"Valid articles: {len(valid_articles)}")
    print(f"Skipped articles: {skipped_count}")

    if not valid_articles:
        print("No valid articles to group.")

        output = {
            "news": news
        }

        with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
            json.dump(output, file, ensure_ascii=False, indent=2)

        return

    print()
    print("Grouping articles...")

    groups = group_articles(
        valid_articles,
        embeddings
    )

    # Map article index → group ID
    article_to_group = {}

    for group in groups:
        for article_index in group["article_indices"]:
            article_to_group[article_index] = group["group_id"]

    # Add group IDs while preserving original news structure
    valid_index = 0

    for article in news:

        scraped_data = article.get("scraped_data", {})

        text = scraped_data.get("text", "")
        status = scraped_data.get("status", "")

        if status != "success" or not text.strip():
            article["group_id"] = None
            continue

        article["group_id"] = article_to_group[valid_index]

        valid_index += 1

    # Remove internal embedding information
    # from anything that could become part of output.
    output = {
        "news": news
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("Grouping completed.")
    print(f"Number of groups: {len(groups)}")
    print(f"Output: {OUTPUT_FILE}")

    # Group statistics
    group_sizes = [
        len(group["article_indices"])
        for group in groups
    ]

    multi_article_groups = sum(
        1 for size in group_sizes
        if size > 1
    )

    singleton_groups = sum(
        1 for size in group_sizes
        if size == 1
    )

    print(f"Groups with multiple articles: {multi_article_groups}")
    print(f"Singleton groups: {singleton_groups}")


if __name__ == "__main__":
    main()
