import streamlit as st
import requests
import asyncio
import pandas as pd
from agents2.profile import ARCHETYPES, ProfileGenerator, MY_PROFILE

# --- Config ---
API_URL = "http://localhost:8000"
st.set_page_config(page_title="AI Analyst Hub", page_icon="📈", layout="wide")

# --- Custom CSS ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #3498db; color: white; }
    .status-box { padding: 20px; border-radius: 10px; background-color: #ffffff; border: 1px solid #e0e0e0; }
    </style>
""", unsafe_allow_html=True)

# --- Sidebar: Profile Management ---
with st.sidebar:
    st.title("👤 User Profile")
    st.subheader("Archetype Sync")
    selected_archetype = st.selectbox("Choose an Archetype", list(ARCHETYPES.keys()))
    
    if st.button("Load Archetype"):
        data = ARCHETYPES[selected_archetype]
        st.session_state['bio'] = data['bio']
        st.session_state['interests'] = ", ".join(data['interests'])
        st.success(f"Loaded {selected_archetype} settings!")

    st.divider()
    
    st.subheader("AI Profile Generator")
    user_name = st.text_input("Name", value=MY_PROFILE.name)
    raw_bio = st.text_area("Tell the AI about your role...", height=150, key="bio")
    
    if st.button("✨ Suggest Interests"):
        generator = ProfileGenerator()
        # Run the async generator
        suggested_profile = asyncio.run(generator.generate_from_bio(user_name, raw_bio))
        st.session_state['interests'] = ", ".join(suggested_profile.interests)
        st.session_state['must_include'] = ", ".join(suggested_profile.must_include)
        st.info("AI has updated your suggested interests below.")

# --- Main UI ---
st.title("🛰️ AI Analyst Command Center")

tab1, tab2, tab3 = st.tabs(["🚀 Execute Pipeline", "📰 Latest News", "📧 Daily Digest"])

with tab1:
    st.header("Trigger Mission")
    col1, col2 = st.columns([2, 1])
    
    with col1:
        query = st.text_input("One-off Search Query (Optional)", placeholder="e.g., Japan's fiscal policy shift...")
        st.caption("Leave blank to use your profile's default interests.")
    
    with col2:
        top_n = st.number_input("Articles per source", min_value=1, max_value=5, value=1)
    
    if st.button("Run Analyst Pipeline"):
        with st.spinner("Agent mission in progress..."):
            try:
                response = requests.post(f"{API_URL}/run-pipeline", json={
                    "user_query": query,
                    "top_n": int(top_n)
                })
                if response.status_code == 202:
                    st.success("✅ Pipeline triggered! The agents are scraping and scoring now.")
                    st.toast("Check 'Latest News' in a few minutes.")
                else:
                    st.error("Failed to start pipeline.")
            except Exception as e:
                st.error(f"Backend connection error: {e}")

with tab2:
    st.header("Top Scored Insights")
    if st.button("Refresh News"):
        try:
            news_data = requests.get(f"{API_URL}/news/today").json()
            if news_data:
                df = pd.DataFrame(news_data)
                # Display articles as cards
                for index, row in df.iterrows():
                    with st.container():
                        st.markdown(f"### {row['article_name']}")
                        st.markdown(f"**Impact Score:** `{row['impact_score']}/100` | [Source]({row['source_link']})")
                        st.write(row['summary'])
                        with st.expander("Why this matters (AI Insight)"):
                            st.write(row['relevance_explanation'])
                        st.divider()
            else:
                st.info("No news found for today. Run the pipeline first!")
        except:
            st.error("Could not reach backend.")

with tab3:
    st.header("Visual Newsletter")
    if st.button("View HTML Digest"):
        try:
            digest_data = requests.get(f"{API_URL}/news/digest").json()
            if digest_data.get("ready"):
                st.components.v1.html(digest_data['html'], height=800, scrolling=True)
            else:
                st.warning("Digest is not ready yet. Ensure the 'Summarizer' agent has finished.")
        except:
            st.error("Backend offline.")