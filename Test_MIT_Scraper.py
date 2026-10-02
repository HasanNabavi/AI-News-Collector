from Scrapers.MIT_Technology_Review import scrape


URL = (
    "https://www.technologyreview.com/"
    "2026/10/01/1145588/"
    "ai-mind-reading-reconstructs-"
    "what-youre-looking-at/"
)


result = scrape(URL)


print("PAGE TYPE:")
print(result["page_type"])

print("\nSTATUS:")
print(result["status"])

print("\nTITLE:")
print(result["title"])

print("\nPUBLISHED:")
print(result["published_at"])

print("\nSTANDFIRST:")
print(result["standfirst"])

print("\nTEXT CHARACTERS:")
print(len(result["text"]))

print("\nMAIN IMAGE:")
print(result["main_image"])

print("\nIMAGES:")
print(len(result["images"]))

print("\nVIDEOS:")
print(len(result["videos"]))

print("\nURL:")
print(result["url"])
