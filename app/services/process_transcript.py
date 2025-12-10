import time
from sqlalchemy.orm import Session
from app.database.repository import Repository
from app.database.models import YouTubeVideo
from app.scrappers.youtube_scraper import YouTubeScraper

class TranscriptService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = Repository(session)
        self.scraper = YouTubeScraper()

    # RENAMED from 'process_pending_transcripts' to 'run'
    def run(self):
        """
        Finds all videos with missing transcripts and fills them in.
        """
        print("🎙️  Starting Transcript Processor...")
        
        # 1. Find videos with NO transcript
        pending_videos = self.session.query(YouTubeVideo).filter(YouTubeVideo.transcript == None).all()
        
        if not pending_videos:
            print("✅ All videos are up to date.")
            return

        print(f"found {len(pending_videos)} pending videos...")

        # 2. Process them
        for video in pending_videos:
            print(f"  Processing: {video.title[:50]}...")
            
            try:
                # Call the Scraper
                transcript_obj = self.scraper.fetch_transcript(video.video_id)
                
                # Check for valid text
                if transcript_obj.text and not transcript_obj.text.startswith("Error"):
                    # Call the Repository to update
                    if self.repo.update_youtube_transcript(video.video_id, transcript_obj.text):
                        print(f"    ✅ Updated ({len(transcript_obj.text)} chars)")
                else:
                    print(f"    ⚠️  Could not fetch: {transcript_obj.text}")
                    
            except Exception as e:
                print(f"    ❌ Error: {e}")
            
            time.sleep(2) # Be polite to API