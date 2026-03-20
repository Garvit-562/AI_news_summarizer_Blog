import feedparser
from newspaper import Article
import time
import json
import google.generativeai as genai

# ==========================================
# 1. SETUP & CONFIGURATION
# ==========================================
# PASTE YOUR API KEY HERE:
GEMINI_API_KEY = "" 
genai.configure(api_key=GEMINI_API_KEY)

# Initialize the Gemini model
model = genai.GenerativeModel('gemini-3.1-flash-lite-preview') # Flash is the fastest model for text tasks

RSS_FEEDS = {
    "Times of India": "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms",
    "The Hindu": "https://www.thehindu.com/news/national/feeder/default.rss",
    "Defense News": "https://www.defensenews.com/arc/outboundfeeds/rss/"
}

scraped_news_data = []

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def get_article_links_from_rss(rss_url, max_links=2): # Reduced to 2 for faster testing
    print(f"Reading RSS feed: {rss_url}")
    feed = feedparser.parse(rss_url)
    return [entry.link for entry in feed.entries[:max_links]]

def extract_article_content(url, source_name):
    print(f"  -> Extracting content from: {url}")
    try:
        article = Article(url)
        article.download()
        article.parse()
        return {
            "source": source_name,
            "title": article.title,
            "url": url,
            "image_url": article.top_image,
            "raw_text": article.text
        }
    except Exception as e:
        print(f"  -> Failed to extract {url}. Error: {e}")
        return None

def analyze_with_ai(text):
    """Sends the raw article text to Gemini for classification and summarization."""
    print("  -> Sending to AI for processing...")
    
    # We ask the AI to output strictly in JSON format so our code can read it easily
    prompt = f"""
    You are an expert news editor. Read the following article text and provide:
    1. A category (Choose ONE: Politics, Technology, Business, Sports, Entertainment, Defense, General)
    2. A 3-bullet point summary (TL;DR)
    3. A short, engaging 100-word blog post about the article.
    
    Respond ONLY with a valid JSON object using these exact keys: "category", "bullet_points", "blog_post".
    
    Article Text:
    {text[:3000]} # We limit to 3000 chars to save tokens and speed things up
    """
    
    try:
        # We force the model to return a JSON object
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        # Convert the AI's JSON text response into a Python dictionary
        return json.loads(response.text)
    except Exception as e:
        print(f"  -> AI Processing Failed. Error: {e}")
        return {
            "category": "Uncategorized", 
            "bullet_points": ["Summary unavailable."], 
            "blog_post": "Blog post unavailable."
        }

# ==========================================
# 3. MAIN PIPELINE
# ==========================================
for source, url in RSS_FEEDS.items():
    print(f"\n--- Processing {source} ---")
    
    article_links = get_article_links_from_rss(url, max_links=2)
    
    for link in article_links:
        # Step A: Scrape
        article_data = extract_article_content(link, source)
        
        if article_data and article_data["raw_text"]:
            # Step B: AI Magic
            ai_results = analyze_with_ai(article_data["raw_text"])
            
            # Step C: Combine everything into one clean dictionary
            final_article = {
                "source": article_data["source"],
                "title": article_data["title"],
                "url": article_data["url"],
                "image_url": article_data["image_url"],
                "category": ai_results["category"],
                "summary_bullets": ai_results["bullet_points"],
                "blog_post": ai_results["blog_post"]
            }
            
            scraped_news_data.append(final_article)
        
        time.sleep(2) # Pause so we don't overwhelm the websites or the API


print("\n=== PIPELINE COMPLETE ===")
# Save the final data to a file so Streamlit can use it
with open("news_data.json", "w", encoding="utf-8") as f:
    json.dump(scraped_news_data, f, indent=4, ensure_ascii=False)

print("Saved all processed news to 'news_data.json'!")