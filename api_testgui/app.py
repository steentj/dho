import streamlit as st
import requests
import webbrowser
from typing import Dict, Any

# --- CONFIGURATION ---
API_ENDPOINT = "http://localhost:8080/search"  # nginx endpoint from docker-compose.yml

def display_search_result(result: Dict[str, Any], index: int):
    """Display a single search result with proper formatting."""
    
    with st.container():
        st.markdown('<div class="search-result">', unsafe_allow_html=True)
        
        # Title and basic info
        titel = result.get('titel', 'Ingen titel')
        forfatter = result.get('forfatter', '')
        
        st.markdown(f'<div class="result-title">📖 {index}. {titel}</div>', unsafe_allow_html=True)
        
        # Metadata
        meta_info = []
        if forfatter:
            meta_info.append(f"👤 Forfatter: {forfatter}")
        
        distance = result.get('min_distance', result.get('distance', 0))
        meta_info.append(f"🎯 Relevans: {1-distance:.1%}")
        
        chunk_count = result.get('chunk_count', 1)
        meta_info.append(f"📄 {chunk_count} tekstafsnit")
        
        pages = result.get('pages', [])
        if pages:
            page_str = f"Side {pages[0]}" if len(pages) == 1 else f"Sider {min(pages)}-{max(pages)}"
            meta_info.append(f"📑 {page_str}")
        
        st.markdown(f'<div class="result-meta">{" • ".join(meta_info)}</div>', unsafe_allow_html=True)
        
        # Content preview
        chunk = result.get('chunk', '')
        if chunk:
            st.markdown('<div class="result-chunk">', unsafe_allow_html=True)
            
            # Split chunks by separator and display each
            chunks = chunk.split('\n\n---\n\n')
            for chunk_part in chunks[:3]:  # Show max 3 chunks to avoid overwhelming
                if chunk_part.strip():
                    st.markdown(chunk_part.strip())
                    if len(chunks) > 1:
                        st.markdown("---")
            
            if len(chunks) > 3:
                st.markdown(f"*... og {len(chunks) - 3} flere tekstafsnit*")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Action buttons
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            user_url = result.get('pdf_navn', '')
            if user_url and st.button("📖 Åbn bog", key=f"open_user_{index}"):
                try:
                    webbrowser.open_new_tab(user_url)
                    st.success("Åbner bog i browser...")
                except Exception as e:
                    st.error(f"Kunne ikke åbne bog: {str(e)}")
        
        with col2:
            internal_url = result.get('internal_url', '')
            if internal_url and st.button("📍 Åbn på specifik side", key=f"open_internal_{index}"):
                try:
                    webbrowser.open_new_tab(internal_url)
                    st.success("Åbner bog på specifik side i browser...")
                except Exception as e:
                    st.error(f"Kunne ikke åbne bog: {str(e)}")
        
        with col3:
            # Copy button for URL
            if st.button("📋", key=f"copy_{index}", help="Kopier link"):
                st.code(user_url)
        
        st.markdown('</div>', unsafe_allow_html=True)

st.set_page_config(
    page_title="Semantic Search API Tester", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0 2rem 0;
        border-bottom: 2px solid #f0f2f6;
        margin-bottom: 2rem;
    }
    .search-result {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 1.5rem;
        margin: 1rem 0;
        background-color: #fafafa;
    }
    .result-title {
        font-size: 1.2rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .result-meta {
        color: #666;
        font-size: 0.9rem;
        margin-bottom: 1rem;
    }
    .result-chunk {
        background-color: white;
        padding: 1rem;
        border-radius: 4px;
        border-left: 4px solid #1f77b4;
        margin: 0.5rem 0;
    }
    .page-info {
        font-weight: bold;
        color: #2e7d32;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">', unsafe_allow_html=True)
st.title("🔎 Dansk Historie Online - Semantisk Søgning")
st.markdown("**API Test Interface**")
st.markdown("Enter your search query below to test the semantic search API through the nginx endpoint.")
st.markdown('</div>', unsafe_allow_html=True)

# Search input
col1, col2 = st.columns([4, 1])
with col1:
    query = st.text_input("Søgeforespørgsel", placeholder="Indtast din søgeforespørgsel her...", label_visibility="collapsed")
with col2:
    search_clicked = st.button("🔍 Søg", use_container_width=True)

# Display API endpoint info
with st.expander("ℹ️ API Information"):
    st.code(f"Endpoint: {API_ENDPOINT}")
    st.write("**Request format:**")
    st.json({"query": "example search text"})
    st.write("**Response format:** List of SearchResult objects with grouped chunks per book")

if search_clicked or query:
    if not query.strip():
        st.warning("⚠️ Indtast venligst en søgeforespørgsel.")
    else:
        with st.spinner("Søger i databasen..."):
            try:
                # Make API request
                response = requests.post(
                    API_ENDPOINT, 
                    json={"query": query.strip()}, 
                    timeout=30,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                results = response.json()
                
                if not results:
                    st.info("📭 Ingen resultater fundet for din søgning.")
                else:
                    st.success(f"✅ Fundet {len(results)} bog(er) med relevante resultater")
                    
                    # Display results
                    for i, result in enumerate(results, 1):
                        display_search_result(result, i)
                        
            except requests.exceptions.ConnectionError:
                st.error("❌ **Connection Error**: Kunne ikke forbinde til API serveren. Kontroller at nginx containeren kører på localhost:8080")
            except requests.exceptions.Timeout:
                st.error("⏱️ **Timeout Error**: API kaldet tog for lang tid. Prøv igen.")
            except requests.exceptions.HTTPError as e:
                st.error(f"❌ **HTTP Error**: {e.response.status_code} - {e.response.text}")
            except requests.exceptions.RequestException as e:
                st.error(f"❌ **Request Error**: {str(e)}")
            except Exception as e:
                st.error(f"❌ **Unexpected Error**: {str(e)}")


# Footer
st.markdown("""
---
*Powered by Streamlit. For help, see the README.md in this folder.*
""")
