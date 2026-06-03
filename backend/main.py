import os
import shutil
from fastapi import FastAPI, BackgroundTasks, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List

from .config import Config
from .db_connector import DBConnector
from .trends_research import TrendsResearcher
from .content_generator import ContentGenerator
from .video_generator import VideoGenerator
from .publisher import Publisher

app = FastAPI(title="Mẹ Bỉm Thông Thái Content Engine API", version="1.0.0")

# Enable CORS for React dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup directories for static files (video previews, cookies, fonts)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
VIDEOS_DIR = os.path.join(STATIC_DIR, "videos")
COOKIES_DIR = os.path.join(BASE_DIR, "cookies")

os.makedirs(VIDEOS_DIR, exist_ok=True)
os.makedirs(COOKIES_DIR, exist_ok=True)

# Serve generated videos statically
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Initialize database
DBConnector.init_db()

# --- REQUEST MODELS ---
class TopicRequest(BaseModel):
    topic: str

class ArticleUpdate(BaseModel):
    title: str
    content: str
    summary: Optional[str] = ""
    category: Optional[str] = "Chăm sóc bé"
    subcategory: Optional[str] = ""
    tags: Optional[str] = ""
    meta_title: Optional[str] = ""
    meta_description: Optional[str] = ""

class FBPostUpdate(BaseModel):
    content: str

class VideoScriptUpdate(BaseModel):
    title: str
    hook: str
    voiceover_text: str
    visual_prompts: Optional[str] = ""
    bg_music: Optional[str] = "lullaby"
    voice_model: Optional[str] = "vi-VN-HoaiMyNeural"

# --- API ENDPOINTS ---

@app.get("/")
def home():
    return {
        "status": "online",
        "message": "Mẹ Bỉm Thông Thái Content Engine is running.",
        "database_type": DBConnector.get_connection_type(),
        "missing_keys": Config.get_missing_keys()
    }

# 1. Trends & Research
@app.get("/api/trends")
def get_trends(limit: int = 15):
    return TrendsResearcher.get_latest_trends(limit)

@app.post("/api/trends/fetch")
def fetch_trends():
    count = TrendsResearcher.update_trends_database()
    return {"message": "Trends updated successfully.", "items_added": count}

# 2. Articles CRUD
@app.get("/api/articles")
def get_articles():
    return DBConnector.execute_query("SELECT * FROM articles ORDER BY created_at DESC")

@app.post("/api/articles/generate")
def generate_article(req: TopicRequest):
    try:
        article_data = ContentGenerator.generate_article(req.topic)
        # Save as draft
        query = """
            INSERT INTO articles (title, content, summary, category, subcategory, tags, status, meta_title, meta_description, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, 'draft', %s, %s, NOW())
            RETURNING id
        """ if DBConnector.get_connection_type() == "postgres" else """
            INSERT INTO articles (title, content, summary, category, subcategory, tags, status, meta_title, meta_description, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'draft', ?, ?, datetime('now'))
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
        res = DBConnector.execute_query(query, params)
        return {"id": res[0]["id"] if res else None, **article_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/articles/{article_id}")
def update_article(article_id: int, req: ArticleUpdate):
    query = """
        UPDATE articles 
        SET title = %s, content = %s, summary = %s, category = %s, subcategory = %s, tags = %s, meta_title = %s, meta_description = %s
        WHERE id = %s
    """ if DBConnector.get_connection_type() == "postgres" else """
        UPDATE articles 
        SET title = ?, content = ?, summary = ?, category = ?, subcategory = ?, tags = ?, meta_title = ?, meta_description = ?
        WHERE id = ?
    """
    params = (req.title, req.content, req.summary, req.category, req.subcategory, req.tags, req.meta_title, req.meta_description, article_id)
    DBConnector.execute_query(query, params)
    return {"message": "Article updated successfully."}

@app.delete("/api/articles/{article_id}")
def delete_article(article_id: int):
    query = "DELETE FROM articles WHERE id = %s" if DBConnector.get_connection_type() == "postgres" else "DELETE FROM articles WHERE id = ?"
    DBConnector.execute_query(query, (article_id,))
    return {"message": "Article deleted."}

# 3. Facebook Posts CRUD
@app.get("/api/facebook-posts")
def get_facebook_posts():
    return DBConnector.execute_query("SELECT * FROM facebook_posts ORDER BY created_at DESC")

@app.post("/api/facebook-posts/generate")
def generate_fb_post(req: TopicRequest):
    try:
        post_data = ContentGenerator.generate_facebook_post(req.topic)
        query = """
            INSERT INTO facebook_posts (content, status, created_at)
            VALUES (%s, 'draft', NOW())
            RETURNING id
        """ if DBConnector.get_connection_type() == "postgres" else """
            INSERT INTO facebook_posts (content, status, created_at)
            VALUES (?, 'draft', datetime('now'))
        """
        res = DBConnector.execute_query(query, (post_data["content"],))
        return {"id": res[0]["id"] if res else None, **post_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/facebook-posts/{post_id}")
def update_fb_post(post_id: int, req: FBPostUpdate):
    query = "UPDATE facebook_posts SET content = %s WHERE id = %s" if DBConnector.get_connection_type() == "postgres" else "UPDATE facebook_posts SET content = ? WHERE id = ?"
    DBConnector.execute_query(query, (req.content, post_id))
    return {"message": "Post updated."}

@app.delete("/api/facebook-posts/{post_id}")
def delete_fb_post(post_id: int):
    query = "DELETE FROM facebook_posts WHERE id = %s" if DBConnector.get_connection_type() == "postgres" else "DELETE FROM facebook_posts WHERE id = ?"
    DBConnector.execute_query(query, (post_id,))
    return {"message": "Post deleted."}

# 4. Video Scripts CRUD & Rendering
@app.get("/api/video-scripts")
def get_video_scripts():
    return DBConnector.execute_query("SELECT * FROM video_scripts ORDER BY created_at DESC")

@app.post("/api/video-scripts/generate")
def generate_video_script(req: TopicRequest):
    try:
        script = ContentGenerator.generate_video_script(req.topic)
        # Format scenes for saving (we compress scenes array to a JSON string)
        scenes_json = json.dumps(script["scenes"], ensure_ascii=False)
        
        query = """
            INSERT INTO video_scripts (title, hook, voiceover_text, visual_prompts, bg_music, voice_model, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, 'draft', NOW())
            RETURNING id
        """ if DBConnector.get_connection_type() == "postgres" else """
            INSERT INTO video_scripts (title, hook, voiceover_text, visual_prompts, bg_music, voice_model, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'draft', datetime('now'))
        """
        params = (
            script["title"],
            script.get("hook", ""),
            " ".join([s["voiceover_text"] for s in script["scenes"]]), # concatenated text
            scenes_json, # visual_prompts stores full JSON list of scenes
            script.get("bg_music", "lullaby"),
            script.get("voice_model", "vi-VN-HoaiMyNeural")
        )
        res = DBConnector.execute_query(query, params)
        return {"id": res[0]["id"] if res else None, **script}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/video-scripts/{script_id}")
def update_video_script(script_id: int, req: VideoScriptUpdate):
    query = """
        UPDATE video_scripts 
        SET title = %s, hook = %s, voiceover_text = %s, visual_prompts = %s, bg_music = %s, voice_model = %s
        WHERE id = %s
    """ if DBConnector.get_connection_type() == "postgres" else """
        UPDATE video_scripts 
        SET title = ?, hook = ?, voiceover_text = ?, visual_prompts = ?, bg_music = ?, voice_model = ?
        WHERE id = ?
    """
    params = (req.title, req.hook, req.voiceover_text, req.visual_prompts, req.bg_music, req.voice_model, script_id)
    DBConnector.execute_query(query, params)
    return {"message": "Script updated."}

@app.delete("/api/video-scripts/{script_id}")
def delete_video_script(script_id: int):
    query = "DELETE FROM video_scripts WHERE id = %s" if DBConnector.get_connection_type() == "postgres" else "DELETE FROM video_scripts WHERE id = ?"
    DBConnector.execute_query(query, (script_id,))
    return {"message": "Script deleted."}

# Background Video Compiler Task
def render_video_background_task(script_id: int, title: str, voice_model: str, scenes_list: list):
    try:
        # Update status to rendering
        status_query = "UPDATE video_scripts SET status = 'rendering' WHERE id = %s" if DBConnector.get_connection_type() == "postgres" else "UPDATE video_scripts SET status = 'rendering' WHERE id = ?"
        DBConnector.execute_query(status_query, (script_id,))
        
        video_filename = f"video_{script_id}.mp4"
        output_path = os.path.join(VIDEOS_DIR, video_filename)
        
        script_data = {
            "title": title,
            "voice_model": voice_model,
            "scenes": scenes_list
        }
        
        success = VideoGenerator.compile_video(script_data, output_path)
        
        if success:
            # Save relative static path
            video_url = f"/static/videos/{video_filename}"
            save_query = """
                UPDATE video_scripts 
                SET status = 'rendered', video_path = %s 
                WHERE id = %s
            """ if DBConnector.get_connection_type() == "postgres" else """
                UPDATE video_scripts 
                SET status = 'rendered', video_path = ? 
                WHERE id = ?
            """
            DBConnector.execute_query(save_query, (video_url, script_id))
        else:
            fail_query = "UPDATE video_scripts SET status = 'failed' WHERE id = %s" if DBConnector.get_connection_type() == "postgres" else "UPDATE video_scripts SET status = 'failed' WHERE id = ?"
            DBConnector.execute_query(fail_query, (script_id,))
    except Exception as ex:
        print(f"Error in video render task: {ex}")
        fail_query = "UPDATE video_scripts SET status = 'failed' WHERE id = %s" if DBConnector.get_connection_type() == "postgres" else "UPDATE video_scripts SET status = 'failed' WHERE id = ?"
        DBConnector.execute_query(fail_query, (script_id,))

@app.post("/api/video-scripts/{script_id}/compile")
def compile_video(script_id: int, background_tasks: BackgroundTasks):
    scripts = DBConnector.execute_query("SELECT * FROM video_scripts WHERE id = %s" if DBConnector.get_connection_type() == "postgres" else "SELECT * FROM video_scripts WHERE id = ?", (script_id,))
    if not scripts:
        raise HTTPException(status_code=404, detail="Script not found.")
    
    script = scripts[0]
    
    # Parse scenes
    try:
        scenes_list = json.loads(script["visual_prompts"])
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid scene structure in script.")
        
    background_tasks.add_task(
        render_video_background_task,
        script_id=script["id"],
        title=script["title"],
        voice_model=script["voice_model"],
        scenes_list=scenes_list
    )
    
    return {"message": "Video compilation started in background."}

# 5. Publishing Endpoints
@app.post("/api/publish/website/{article_id}")
def publish_website(article_id: int):
    articles = DBConnector.execute_query("SELECT * FROM articles WHERE id = %s" if DBConnector.get_connection_type() == "postgres" else "SELECT * FROM articles WHERE id = ?", (article_id,))
    if not articles:
        raise HTTPException(status_code=404, detail="Article not found.")
    
    article = articles[0]
    try:
        Publisher.publish_to_website(article)
        # Update original status to published
        update_query = "UPDATE articles SET status = 'published', published_at = NOW() WHERE id = %s" if DBConnector.get_connection_type() == "postgres" else "UPDATE articles SET status = 'published', published_at = datetime('now') WHERE id = ?"
        DBConnector.execute_query(update_query, (article_id,))
        return {"message": "Article published to website successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Website publishing failed: {str(e)}")

@app.post("/api/publish/facebook/{post_id}")
def publish_facebook(post_id: int):
    posts = DBConnector.execute_query("SELECT * FROM facebook_posts WHERE id = %s" if DBConnector.get_connection_type() == "postgres" else "SELECT * FROM facebook_posts WHERE id = ?", (post_id,))
    if not posts:
        raise HTTPException(status_code=404, detail="Post not found.")
    
    post = posts[0]
    try:
        fb_id = Publisher.publish_to_facebook_page({"content": post["content"]})
        update_query = "UPDATE facebook_posts SET status = 'published', fb_post_id = %s, published_at = NOW() WHERE id = %s" if DBConnector.get_connection_type() == "postgres" else "UPDATE facebook_posts SET status = 'published', fb_post_id = ?, published_at = datetime('now') WHERE id = ?"
        DBConnector.execute_query(update_query, (fb_id, post_id))
        return {"message": "Post published to FB Page successfully.", "post_id": fb_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Playwright Video Upload Trigger
def upload_video_background_task(script_id: int, platform: str, video_path: str, caption: str):
    abs_video_path = os.path.join(STATIC_DIR, video_path.lstrip("/static"))
    
    success = False
    error = ""
    
    if platform == "tiktok":
        success, error = Publisher.upload_to_tiktok(abs_video_path, caption)
    elif platform == "facebook":
        success, error = Publisher.upload_to_facebook_reels(abs_video_path, caption)
        
    # Update publish status in DB
    col = f"{platform}_published"
    if success:
        query = f"UPDATE video_scripts SET {col} = 1 WHERE id = %s" if DBConnector.get_connection_type() == "postgres" else f"UPDATE video_scripts SET {col} = 1 WHERE id = ?"
        DBConnector.execute_query(query, (script_id,))
        print(f"Video {script_id} published successfully to {platform}.")
    else:
        print(f"Video {script_id} upload failed to {platform}: {error}")

@app.post("/api/publish/video/{script_id}")
def publish_video(script_id: int, platform: str, background_tasks: BackgroundTasks):
    if platform not in ["tiktok", "facebook"]:
        raise HTTPException(status_code=400, detail="Invalid platform. Choose 'tiktok' or 'facebook'.")
        
    scripts = DBConnector.execute_query("SELECT * FROM video_scripts WHERE id = %s" if DBConnector.get_connection_type() == "postgres" else "SELECT * FROM video_scripts WHERE id = ?", (script_id,))
    if not scripts:
        raise HTTPException(status_code=404, detail="Script not found.")
        
    script = scripts[0]
    if script["status"] != "rendered":
        raise HTTPException(status_code=400, detail="Video is not rendered yet. Compile it first.")
        
    caption = f"{script['title']}\n\n#mebimthongthai #nuoiconkhoahoc #chamsocbe"
    background_tasks.add_task(
        upload_video_background_task,
        script_id=script_id,
        platform=platform,
        video_path=script["video_path"],
        caption=caption
    )
    
    return {"message": f"Upload process to {platform.upper()} started in background."}

# Cookie Upload for browser automation sessions
@app.post("/api/cookies/{platform}")
async def upload_cookies(platform: str, file: UploadFile = File(...)):
    if platform not in ["tiktok", "facebook", "youtube"]:
        raise HTTPException(status_code=400, detail="Invalid platform.")
        
    dest_path = os.path.join(COOKIES_DIR, f"{platform}.json")
    try:
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"message": f"Cookies for {platform.upper()} uploaded successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
