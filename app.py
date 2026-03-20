import streamlit as st
import json
import os

# ==========================================
# 1. PAGE SETUP
# ==========================================
st.set_page_config(page_title="AI News Navigator", page_icon="📰", layout="wide")
st.title("📰 AI News Navigator")
st.markdown("Your daily news, summarized and categorized by AI.")

# ==========================================
# 2. LOAD THE DATA
# ==========================================
# We use a function to read the JSON file we created in Phase 2
def load_data():
    if os.path.exists("news_data.json"):
        with open("news_data.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return []

news_articles = load_data()

# ==========================================
# 3. SIDEBAR & FILTERS
# ==========================================
if not news_articles:
    st.warning("No news data found! Please run `python scrapper.py` first.")
else:
    # Get a list of unique categories from our data to build the filter menu
    categories = ["All News"] + list(set([article.get("category", "General") for article in news_articles]))
    
    st.sidebar.header("Filter by Category")
    selected_category = st.sidebar.radio("Select a Genre:", categories)

    # Filter the articles based on the user's sidebar selection
    if selected_category == "All News":
        filtered_articles = news_articles
    else:
        filtered_articles = [article for article in news_articles if article.get("category") == selected_category]

    st.header(f"Trending in: {selected_category}")
    st.markdown("---")

    # ==========================================
# 4. DISPLAY THE FLASHCARDS
# ==========================================
    # We use columns to create a grid layout (2 columns per row)
    cols = st.columns(2)
    
    for index, article in enumerate(filtered_articles):
        # Alternate between the left and right column
        col = cols[index % 2]
        
        with col:
            # Create a visual card container
            with st.container(border=True):
                # 1. Show the Image (if it exists)
                if article.get("image_url"):
                    st.image(article["image_url"], use_container_width=True)
                
                # 2. Show Source and Category tags
                st.caption(f"**Source:** {article['source']} | **Category:** {article['category']}")
                
                # 3. Show Headline
                st.subheader(article["title"])
                
                # 4. The Interactive "Flashcard" Flip (Expander)
                with st.expander("Read Simplified Article"):
                    st.markdown("### Quick Summary")
                    # Display the bullet points
                    for bullet in article.get("summary_bullets", []):
                        st.markdown(f"- {bullet}")
                    
                    st.markdown("### AI Blog Post")
                    # Display the AI generated blog post
                    st.write(article.get("blog_post", ""))
                    
                    # Provide a link back to the original article
                    st.markdown(f"[Read full original article here]({article['url']})")