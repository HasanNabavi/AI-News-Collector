import json

# Load news sources
with open("sources.json", "r", encoding="utf-8") as file:
    data = json.load(file)

sources = data["sources"]

print("News sources:")
print()

for source in sources:
    print(f"- {source['name']} ({source['category']})")
