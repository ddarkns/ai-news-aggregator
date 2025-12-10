import sys
import os
import argparse  # <--- NEW IMPORT

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.create_tables import init_db
from app.database.connection import get_db
from app.runner import run_pipeline
from app.services.process_transcript import TranscriptService

def main():
    # 1. Setup Argument Parser
    parser = argparse.ArgumentParser(description="Run The Final Cook Pipeline")
    parser.add_argument("--skip-scrape", action="store_true", help="Skip Phase 1 (Scraping) and only run Phase 2 (Transcripts)")
    args = parser.parse_args()

    print("🎬 Starting The Final Cook Application...")
    
    # Phase 1: Database Check (Always do this)
    print("\n[1/3] Initializing Database...")
    try:
        init_db()
    except Exception as e:
        print(f"❌ Critical Error: {e}")
        return

    # Phase 2: Discovery (Scraping) - CONDITIONAL
    if not args.skip_scrape:
        print("\n[2/3] Running Scraping Pipeline (Discovery)...")
        try:
            results = run_pipeline()
        except Exception as e:
            print(f"\n❌ Scraping Pipeline failed: {e}")
    else:
        print("\n[2/3] ⏩ SKIPPING Scraping Pipeline (User requested)")

    # Phase 3: Enrichment (Transcripts) - ALWAYS RUN
    print("\n[3/3] Processing Transcripts (Enrichment)...")
    
    db_gen = get_db()
    session = next(db_gen)

    try:
        processor = TranscriptService(session)
        processor.run()
    except Exception as e:
        print(f"❌ Transcript processing failed: {e}")
    finally:
        session.close()

    print("\n🎉 EXECUTION COMPLETE")

if __name__ == "__main__":
    main()