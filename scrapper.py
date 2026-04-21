import feedparser
from newspaper import Article
import time
import json
import os
import re
import google.generativeai as genai

# ==========================================
# 1. SETUP & CONFIGURATION
# ==========================================
GEMINI_API_KEY = ""   # ← paste your key here

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

# ==========================================
# 2. RSS FEED SOURCES
# ==========================================
RSS_FEEDS = {
    "Times of India": "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms",
    "The Hindu":      "https://www.thehindu.com/news/national/feeder/default.rss",
    "Defense News":   "https://www.defensenews.com/arc/outboundfeeds/rss/",
    "TechCrunch":     "https://techcrunch.com/feed/",
    "BBC News":       "https://feeds.bbci.co.uk/news/rss.xml",
    "Reuters":        "https://feeds.reuters.com/reuters/topNews",
    "ESPN":           "https://www.espn.com/espn/rss/news",
}

ARTICLES_PER_FEED = 3

scraped_news_data = []

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================
def get_article_links_from_rss(rss_url, max_links=ARTICLES_PER_FEED):
    print(f"  Reading RSS: {rss_url}")
    try:
        feed = feedparser.parse(rss_url)
        links = [entry.link for entry in feed.entries[:max_links] if hasattr(entry, "link")]
        print(f"  Found {len(links)} articles.")
        return links
    except Exception as e:
        print(f"  RSS parse error: {e}")
        return []


def extract_article_content(url, source_name):
    print(f"  Extracting: {url[:60]}...")
    try:
        article = Article(url)
        article.download()
        article.parse()
        if len(article.text.strip()) < 100:
            print("  Skipped - too short or paywalled.")
            return None
        return {
            "source":    source_name,
            "title":     article.title,
            "url":       url,
            "image_url": article.top_image or "",
            "raw_text":  article.text,
        }
    except Exception as e:
        print(f"  Extraction failed: {e}")
        return None


def extract_json_from_response(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    cleaned = re.sub(r"```(?:json)?", "", text).strip().rstrip("```").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


def analyze_with_ai(article: dict) -> dict:
    print("  Sending to Gemini...")

    prompt = f"""You are a senior news editor. Read this article and respond with ONLY a raw JSON object - no markdown, no explanation, nothing else.

Required JSON structure:
{{
  "category": "<one of: Politics, Technology, Business, Sports, Entertainment, Defense, Science, Health, General>",
  "summary_bullets": ["<bullet 1>", "<bullet 2>", "<bullet 3>"],
  "blog_post": "<engaging 100-120 word blog post about the article>",
  "tags": ["<tag1>", "<tag2>", "<tag3>"]
}}

Article Title: {article['title']}

Article Text:
{article['raw_text'][:3500]}
"""

    try:
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        result = extract_json_from_response(response.text)

        if result and all(k in result for k in ("category", "summary_bullets", "blog_post")):
            return result
        else:
            print(f"  Bad JSON, using fallback. Raw: {response.text[:200]}")
    except Exception as e:
        print(f"  AI call failed: {e}")

    return {
        "category":        "General",
        "summary_bullets": ["Summary unavailable.", "Please read the full article.", ""],
        "blog_post":       "Full article available at the source link.",
        "tags":            [],
    }


# ==========================================
# 4. MAIN PIPELINE
# ==========================================
print("\n Starting AI News Navigator scraper...\n")

for source, feed_url in RSS_FEEDS.items():
    print(f"\n--- {source} ---")
    links = get_article_links_from_rss(feed_url)

    for link in links:
        article_data = extract_article_content(link, source)
        if not article_data:
            continue

        ai = analyze_with_ai(article_data)

        final = {
            "source":          article_data["source"],
            "title":           article_data["title"],
            "url":             article_data["url"],
            "image_url":       article_data["image_url"],
            "category":        ai.get("category", "General"),
            "summary_bullets": ai.get("summary_bullets", []),
            "blog_post":       ai.get("blog_post", ""),
            "tags":            ai.get("tags", []),
        }

        scraped_news_data.append(final)
        print(f"  [{final['category']}] {final['title'][:60]}")
        time.sleep(1.5)

# ==========================================
# 5. SAVE OUTPUT
# ==========================================
with open("news_data.json", "w", encoding="utf-8") as f:
    json.dump(scraped_news_data, f, indent=4, ensure_ascii=False)

print(f"\nDone! Saved {len(scraped_news_data)} articles to 'news_data.json'")
print("   Run `streamlit run app.py` to launch the UI.\n")