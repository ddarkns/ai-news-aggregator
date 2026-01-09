import os
import json
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

# --- 1. The Core Schema ---
class UserProfile(BaseModel):
    name: str = Field(description="User's full name")
    bio: str = Field(description="A detailed paragraph about the user's role and technical focus")
    interests: List[str] = Field(default_factory=list, description="Primary technical topics")
    must_include: List[str] = Field(default_factory=list, description="Keywords that trigger high priority")
    ignore_topics: List[str] = Field(default_factory=list, description="Topics to filter out entirely")
    preferred_depth: str = Field(default="Technical", description="Options: Technical, Research, Business, or High-Level")
    custom_sources: Dict[str, str] = Field(default_factory=dict, description="Name and RSS URL pairs")

# --- 2. Predefined Archetypes (The Buttons) ---
ARCHETYPES = {
    "AI_ENGINEER": {
        "bio": "I build production-grade AI systems using LangGraph, CrewAI, and vector databases like PGVector. I care about agentic orchestration, cost-efficiency, and low-latency inference.",
        "interests": ["LangGraph", "Multi-Agent Systems", "RAG", "Function Calling"],
        "must_include": ["Python SDK", "State Management", "Fine-tuning"],
        "ignore_topics": ["Crypto", "Metaverse", "Beginner Python Tutorials"],
        "preferred_depth": "Technical"
    },
    "RESEARCH_SCIENTIST": {
        "bio": "I track the latest breakthroughs in LLM architectures, scaling laws, and reinforcement learning. I need to know about Arxiv papers and benchmark results.",
        "interests": ["Transformers", "Scaling Laws", "RLHF", "Interpretability"],
        "must_include": ["Benchmark", "Architecture", "Paper", "Weights"],
        "ignore_topics": ["SaaS Marketing", "UI Design", "Startup funding"],
        "preferred_depth": "Research"
    },
    "DEVOPS_ARCHITECT": {
        "bio": "I focus on deploying AI at scale. I care about Kubernetes, Docker, database reliability, and CI/CD for machine learning (MLOps).",
        "interests": ["Kubernetes", "PostgreSQL", "MLOps", "Docker", "Scalability"],
        "must_include": ["Latency", "Uptime", "High Availability", "Terraform"],
        "ignore_topics": ["Front-end Frameworks", "UX Research", "Sales Strategy"],
        "preferred_depth": "Technical"
    }
}

# --- 3. AI Suggestion Logic ---
class ProfileGenerator:
    def __init__(self):
        self.llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.7)
        self.parser = PydanticOutputParser(pydantic_object=UserProfile)

    async def generate_from_bio(self, user_name: str, raw_bio: str) -> UserProfile:
        """
        Takes a name and a rough bio, and uses AI to suggest the rest.
        """
        prompt = ChatPromptTemplate.from_template("""
            You are a Professional Career Profile Assistant. 
            Given the following rough bio, create a structured UserProfile.
            Suggest technical interests, must-include keywords, and ignore-topics 
            that would make a news aggregator highly relevant for this person.

            USER NAME: {name}
            ROUGH BIO: {bio}

            {format_instructions}
        """)

        chain = prompt | self.llm | self.parser
        
        # In a real app, this would be an async call
        return chain.invoke({
            "name": user_name, 
            "bio": raw_bio,
            "format_instructions": self.parser.get_format_instructions()
        })

# --- 4. Final Export for the System ---
# In a real UI, this would be loaded from a database or JSON file
MY_PROFILE = UserProfile(
    name="Krish",
    bio="Macroeconomic and Political Analyst focusing on global market trends, fiscal policy, and geopolitical stability.",
    interests=["Global Markets", "Fiscal Policy", "Geopolitics", "Central Bank Decisions", "Trade Agreements"],
    must_include=["Inflation", "Interest Rates", "Elections", "GDP", "Sanctions", "Regulatory Changes"],
    ignore_topics=["Sports", "Celebrity News", "Entertainment", "Consumer Tech Reviews"],
    preferred_depth="Analytical",
    custom_sources={
        "reuters_business": "https://www.reutersagency.com/feed/?best-topics=business&post_type=best",
        "ft_global_economy": "https://www.ft.com/global-economy?format=rss",
        "economist_politics": "https://www.economist.com/international/rss.xml"
    }
)