import streamlit as st
import requests
import webbrowser
from urllib.parse import urlparse

# --- CONFIGURATION ---
API_ENDPOINT = "http://localhost:8080/semantic_search"  # Change to your nginx endpoint

st.set_page_config(page_title="Semantic Search API Tester", layout="centered")
st.title("🔎 Semantic Search API Tester")
st.markdown("""
Enter your search query below to test the semantic search API. Results will appear with clickable links.
""")

query = st.text_input("Search Query", "", placeholder="Type your search here...")

if st.button("Search"):
    if not query.strip():
        st.warning("Please enter a search query.")
    else:
        with st.spinner("Searching..."):
            try:
                response = requests.post(API_ENDPOINT, json={"query": query}, timeout=15)
                response.raise_for_status()
                data = response.json()
                # Expecting grouped results: { group: [ {title, url, ...}, ... ] }
                if not data:
                    st.info("No results found.")
                else:
                    for group, results in data.items():
                        st.subheader(group)
                        for item in results:
                            title = item.get("title", "(No Title)")
                            url = item.get("url")
                            snippet = item.get("snippet", "")
                            if url:
                                st.markdown(f"**[{title}]({url})**", unsafe_allow_html=True)
                                if st.button(f"Open '{title}'", key=f"open_{url}"):
                                    webbrowser.open_new_tab(url)
                            else:
                                st.markdown(f"**{title}**")
                            if snippet:
                                st.caption(snippet)
                            st.markdown("---")
            except requests.exceptions.RequestException as e:
                st.error(f"API connection error: {e}")
            except Exception as e:
                st.error(f"Unexpected error: {e}")

st.markdown("""
---
*Powered by Streamlit. For help, see the README.md in this folder.*
""")
