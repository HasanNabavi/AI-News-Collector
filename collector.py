import json

# Load news sources
with open("sources.json", "r", encoding="utf-8") as file:
    sources_data = json.load(file)

sources = sources_data["sources"]

# Load news
with open("news.json", "r", encoding="utf-8") as file:
    news_data = json.load(file)

news = news_data["news"]

print("News sources:")
print()

for source in sources:
    print(f"- {source['name']} ({source['category']})")

print()
print(f"Total sources: {len(sources)}")
print(f"Total news: {len(news)}")
