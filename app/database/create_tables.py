import sys
import os

# Fix path to find 'app' (Goes up 3 levels from this file)
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.database.connection import engine
from app.database.models import Base, OpenAIArticle, AnthropicArticle, YouTubeVideo

def init_db():
    print("🔄 Connecting to database...")
    # Base.metadata.drop_all(bind=engine) # Uncomment to reset DB
    print("🛠️  Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created successfully!")

if __name__ == "__main__":
    init_db()