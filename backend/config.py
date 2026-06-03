import os
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()

class Config:
    PORT = int(os.getenv("PORT", 8000))
    HOST = os.getenv("HOST", "0.0.0.0")
    
    # Gemini API Key (For Content Generation & Planning)
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    
    # Neon Postgres Connection URL
    DATABASE_URL = os.getenv("DATABASE_URL", "")
    
    # Facebook Graph API Config
    FB_PAGE_ID = os.getenv("FB_PAGE_ID", "")
    FB_PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN", "")
    
    # Pexels API Key for visual assets matching
    PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
    
    # Playwright Cookies paths
    TIKTOK_COOKIES_PATH = os.getenv("TIKTOK_COOKIES_PATH", "cookies/tiktok.json")
    FACEBOOK_COOKIES_PATH = os.getenv("FACEBOOK_COOKIES_PATH", "cookies/facebook.json")
    YOUTUBE_COOKIES_PATH = os.getenv("YOUTUBE_COOKIES_PATH", "cookies/youtube.json")

    @classmethod
    def get_missing_keys(cls):
        missing = []
        if not cls.GEMINI_API_KEY:
            missing.append("GEMINI_API_KEY")
        if not cls.DATABASE_URL:
            missing.append("DATABASE_URL")
        return missing
