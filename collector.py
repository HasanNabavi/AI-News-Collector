import json
import feedparser

# Load news sources
with open("sources.json", "r", encoding="utf-8") as file:
    sources_data = json.load(file)

sources = sources_data["sources"]

print("News sources:")
print()

for source in sources:
    print(f"- {source['name']}")
    print(f"  RSS: {source['rss_url']}")
    print()

print(f"Total sources: {len(sources)}")
