import streamlit as st
import requests
import json

st.set_page_config(page_title="Agents2 News Control", page_icon="🤖")

st.title("🤖 Agents2: Personal News Engine")
st.markdown("Customize your profile and trigger your AI agent workforce.")

with st.sidebar:
    st.header("👤 User Profile")
    user_name = st.text_input("Full Name", value="Krish")
    user_email = st.text_input("Recipient Email")
    
    st.header("🎯 Interests")
    interests = st.text_area("Core Interests (comma separated)", 
                            value="LangGraph, Multi-Agent Systems, PostgreSQL")
    must_include = st.text_area("Must Include Keywords", 
                               value="Agents, Persistence, Vector DB")

st.header("🚀 Trigger Today's Digest")
query = st.text_area("What should the agents look for today?", 
                     value="Latest AI research from Anthropic and OpenAI, and any Indian tech news from TOI")

if st.button("🔥 Run Pipeline & Send Email"):
    if not user_email:
        st.error("Please enter an email address in the sidebar.")
    else:
        payload = {
            "name": user_name,
            "email": user_email,
            "interests": [i.strip() for i in interests.split(",")],
            "must_include": [m.strip() for m in must_include.split(",")],
            "query": query
        }
        
        with st.spinner("Communicating with Backend..."):
            try:
                response = requests.post("http://localhost:8000/trigger-digest", json=payload)
                if response.status_code == 200:
                    st.success("✅ Success! The agents are now scraping, cleaning, and scoring. Check your email in a few minutes.")
                    st.balloons()
                else:
                    st.error("❌ Backend Error: " + response.text)
            except Exception as e:
                st.error(f"❌ Could not connect to FastAPI: {e}")

st.divider()
st.info("The pipeline runs in the background using LangGraph. You can check your terminal logs to see the agents working in real-time.")