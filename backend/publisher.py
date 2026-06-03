import httpx
import os
import json
from datetime import datetime
from playwright.sync_api import sync_playwright
from db_connector import DBConnector
from config import Config

class Publisher:

    @classmethod
    def publish_to_website(cls, article_data):
        """Publishes an article directly into the website's articles database."""
        # Insert article into database
        query = """
            INSERT INTO articles (title, content, summary, category, subcategory, tags, status, meta_title, meta_description, created_at, published_at)
            VALUES (%s, %s, %s, %s, %s, %s, 'published', %s, %s, NOW(), NOW())
            RETURNING id
        """ if DBConnector.get_connection_type() == "postgres" else """
            INSERT INTO articles (title, content, summary, category, subcategory, tags, status, meta_title, meta_description, created_at, published_at)
            VALUES (?, ?, ?, ?, ?, ?, 'published', ?, ?, datetime('now'), datetime('now'))
        """
        
        params = (
            article_data["title"],
            article_data["content"],
            article_data.get("summary", ""),
            article_data.get("category", "Chăm sóc bé"),
            article_data.get("subcategory", ""),
            article_data.get("tags", ""),
            article_data.get("meta_title", article_data["title"]),
            article_data.get("meta_description", article_data.get("summary", ""))
        )
        
        try:
            res = DBConnector.execute_query(query, params)
            article_id = res[0]["id"] if res else None
            print(f"Article published successfully to website with ID: {article_id}")
            return article_id
        except Exception as e:
            print(f"Failed to publish article to website database: {e}")
            raise e

    @classmethod
    def publish_to_facebook_page(cls, post_data):
        """Publishes a text post to the configured Facebook Page via Graph API."""
        if not Config.FB_PAGE_ID or not Config.FB_PAGE_ACCESS_TOKEN:
            print("Facebook API credentials missing. Skipping Graph API publish.")
            # Mock publish
            post_id = f"fb_mock_{int(datetime.now().timestamp())}"
            cls._log_fb_post(post_data["content"], "published", post_id)
            return post_id

        url = f"https://graph.facebook.com/v19.0/{Config.FB_PAGE_ID}/feed"
        payload = {
            "message": post_data["content"],
            "access_token": Config.FB_PAGE_ACCESS_TOKEN
        }
        
        if post_data.get("link"):
            payload["link"] = post_data["link"]

        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.post(url, data=payload)
                if response.status_code == 200:
                    res_data = response.json()
                    post_id = res_data.get("id")
                    print(f"Post published to FB Page successfully. Post ID: {post_id}")
                    cls._log_fb_post(post_data["content"], "published", post_id)
                    return post_id
                else:
                    error_msg = response.text
                    print(f"Facebook Graph API error: {error_msg}")
                    cls._log_fb_post(post_data["content"], "failed", None)
                    raise Exception(f"Facebook API failed: {error_msg}")
        except Exception as e:
            print(f"Error calling Facebook Graph API: {e}")
            cls._log_fb_post(post_data["content"], "failed", None)
            raise e

    @classmethod
    def _log_fb_post(cls, content, status, post_id):
        """Saves publishing state of Facebook posts into local DB."""
        query = """
            INSERT INTO facebook_posts (content, status, fb_post_id, created_at, published_at)
            VALUES (%s, %s, %s, NOW(), NOW())
        """ if DBConnector.get_connection_type() == "postgres" else """
            INSERT INTO facebook_posts (content, status, fb_post_id, created_at, published_at)
            VALUES (?, ?, ?, datetime('now'), datetime('now'))
        """
        try:
            DBConnector.execute_query(query, (content, status, post_id))
        except Exception as ex:
            print(f"Error logging FB post: {ex}")

    @classmethod
    def upload_to_tiktok(cls, video_path, caption):
        """Uses Playwright browser automation to upload video to TikTok Creator Center."""
        cookies_path = Config.TIKTOK_COOKIES_PATH
        
        if not os.path.exists(cookies_path):
            print(f"TikTok cookies file not found at: {cookies_path}. Skipping automation upload.")
            return False, "Cookies missing. Please log in and save cookies via dashboard."
            
        print("Launching Playwright to upload video to TikTok...")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                # Create a context with saved cookies
                context = browser.new_context(
                    viewport={"width": 1280, "height": 720},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                
                # Load cookies
                with open(cookies_path, "r") as f:
                    cookies = json.load(f)
                    context.add_cookies(cookies)
                
                page = context.new_page()
                
                # Navigate to TikTok upload center
                page.goto("https://www.tiktok.com/creator-center/upload?lang=vi-VN", wait_until="domcontentloaded")
                page.wait_for_timeout(3000)
                
                # Check if login was successful
                if "login" in page.url:
                    browser.close()
                    return False, "Session expired. Please update cookies."
                
                # Wait for file input element and upload video
                page.wait_for_selector("input[type='file']", timeout=15000)
                file_input = page.locator("input[type='file']")
                file_input.set_input_files(video_path)
                
                print("Video file selected. Waiting for upload to complete...")
                page.wait_for_timeout(10000) # Wait for initial processing
                
                # Locate Caption input box and enter text
                # TikTok uses an editor element for caption input
                editor_selector = "[contenteditable='true']"
                page.wait_for_selector(editor_selector, timeout=15000)
                page.locator(editor_selector).clear()
                page.locator(editor_selector).fill(caption)
                
                print("Caption filled. Publishing video...")
                # Wait for publish button (usually class or text containing 'Đăng' or 'Post')
                publish_btn = page.locator("button:has-text('Đăng')")
                publish_btn.wait_for(state="visible", timeout=15000)
                publish_btn.click()
                
                page.wait_for_timeout(5000) # Wait to ensure submit action takes effect
                
                browser.close()
                return True, "Success"
        except Exception as e:
            print(f"Playwright TikTok upload failed: {e}")
            return False, str(e)

    @classmethod
    def upload_to_facebook_reels(cls, video_path, caption):
        """Uses Playwright browser automation to upload video to Facebook Creator Studio/Reels."""
        cookies_path = Config.FACEBOOK_COOKIES_PATH
        
        if not os.path.exists(cookies_path):
            print(f"Facebook cookies file not found at: {cookies_path}. Skipping Reels upload.")
            return False, "Cookies missing."

        print("Launching Playwright to upload video to Facebook Reels...")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={"width": 1280, "height": 720},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                
                with open(cookies_path, "r") as f:
                    cookies = json.load(f)
                    context.add_cookies(cookies)
                
                page = context.new_page()
                page.goto("https://www.facebook.com/reels/create", wait_until="domcontentloaded")
                page.wait_for_timeout(5000)
                
                # Check login
                if "login" in page.url:
                    browser.close()
                    return False, "Session expired."
                
                # Upload file
                page.wait_for_selector("input[type='file']", timeout=15000)
                page.locator("input[type='file']").set_input_files(video_path)
                page.wait_for_timeout(10000)
                
                # Add Caption
                caption_input = page.locator("textarea[placeholder*='Mô tả']")
                if caption_input.count() > 0:
                    caption_input.first.fill(caption)
                
                # Click Next buttons
                # Facebook Reels creation has multiple wizard steps (Upload -> Trim -> Share)
                for _ in range(3):
                    next_btn = page.locator("div[role='button']:has-text('Tiếp'), div[role='button']:has-text('Tiếp theo'), div[role='button']:has-text('Đăng')")
                    if next_btn.count() > 0:
                        next_btn.first.click()
                        page.wait_for_timeout(3000)
                
                browser.close()
                return True, "Success"
        except Exception as e:
            print(f"Playwright FB Reels upload failed: {e}")
            return False, str(e)
