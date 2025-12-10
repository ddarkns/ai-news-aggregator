import sys
import os

# Add the project root directory to Python's search path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.config import settings

# 1. Create Engine using the URL from your settings
# We use echo=False to keep logs clean (set to True to see raw SQL queries)
engine = create_engine(settings.POSTGRES_URL, echo=False)

# 2. Session Factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 3. Dependency function
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()