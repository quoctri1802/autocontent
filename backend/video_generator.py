import os
import asyncio
import httpx
import random
from PIL import Image, ImageDraw, ImageFont
import edge_tts
from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip, VideoFileClip, concatenate_videoclips
from .config import Config

class VideoGenerator:
    # 9:16 vertical video resolution for TikTok/Reels
    VIDEO_WIDTH = 1080
    VIDEO_HEIGHT = 1920

    @classmethod
    def _download_font_if_needed(cls):
        """Downloads Roboto-Bold from Google Fonts if not present locally."""
        font_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
        os.makedirs(font_dir, exist_ok=True)
        font_path = os.path.join(font_dir, "Roboto-Bold.ttf")
        
        if not os.path.exists(font_path):
            print("Downloading Roboto-Bold.ttf from Google Fonts...")
            url = "https://github.com/google/fonts/raw/main/apache/roboto/static/Roboto-Bold.ttf"
            try:
                with httpx.Client(timeout=15.0) as client:
                    response = client.get(url)
                    if response.status_code == 200:
                        with open(font_path, "wb") as f:
                            f.write(response.content)
                        print("Font downloaded successfully.")
                    else:
                        print("Failed to download font. Will fallback to system font.")
            except Exception as e:
                print(f"Error downloading font: {e}")
                
        return font_path if os.path.exists(font_path) else "arial.ttf"

    @classmethod
    async def synthesize_speech(cls, text, voice, output_path):
        """Synthesizes text to speech using edge-tts and saves as mp3."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)

    @classmethod
    def fetch_pexels_image(cls, query, output_path):
        """Fetches and downloads a stock image from Pexels API."""
        if not Config.PEXELS_API_KEY:
            return False

        headers = {"Authorization": Config.PEXELS_API_KEY}
        url = f"https://api.pexels.com/v1/search?query={query}&orientation=portrait&per_page=1"
        
        try:
            with httpx.Client(headers=headers, timeout=10.0) as client:
                response = client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("photos"):
                        image_url = data["photos"][0]["src"]["large2x"]
                        # Download image
                        img_response = client.get(image_url)
                        if img_response.status_code == 200:
                            os.makedirs(os.path.dirname(output_path), exist_ok=True)
                            with open(output_path, "wb") as f:
                                f.write(img_response.content)
                            return True
        except Exception as e:
            print(f"Pexels download error for '{query}': {e}")
        return False

    @classmethod
    def generate_pastel_background(cls, index, text, output_path):
        """Generates a beautiful gradient background as a fallback image."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Soft pastel brand colors
        gradients = [
            ((255, 240, 242), (252, 165, 179)), # Pink pastel
            ((240, 250, 245), (168, 230, 207)), # Mint pastel
            ((250, 248, 242), (239, 229, 209)), # Cream pastel
            ((235, 245, 255), (179, 218, 255))  # Light blue pastel
        ]
        
        color_start, color_end = gradients[index % len(gradients)]
        
        # Create gradient image
        base = Image.new("RGBA", (cls.VIDEO_WIDTH, cls.VIDEO_HEIGHT), color_start)
        top = Image.new("RGBA", (cls.VIDEO_WIDTH, cls.VIDEO_HEIGHT), color_end)
        
        # Blend gradient vertically
        mask = Image.new("L", (cls.VIDEO_WIDTH, cls.VIDEO_HEIGHT))
        mask_data = []
        for y in range(cls.VIDEO_HEIGHT):
            mask_val = int(255 * (y / cls.VIDEO_HEIGHT))
            mask_data.extend([mask_val] * cls.VIDEO_WIDTH)
        mask.putdata(mask_data)
        
        gradient_img = Image.composite(top, base, mask)
        draw = ImageDraw.Draw(gradient_img)
        
        # Draw some soft decorative circles
        draw.ellipse([100, 200, 500, 600], fill=(255, 255, 255, 60))
        draw.ellipse([600, 1200, 1100, 1700], fill=(255, 255, 255, 60))
        
        # Draw brand header
        font_path = cls._download_font_if_needed()
        try:
            brand_font = ImageFont.truetype(font_path, 40)
            draw.text((cls.VIDEO_WIDTH // 2, 180), "MẸ BỈM THÔNG THÁI", fill=(224, 77, 101, 200), font=brand_font, anchor="mm")
            draw.text((cls.VIDEO_WIDTH // 2, 230), "Cam nang nuoi day con khoa hoc", fill=(80, 80, 80, 150), font=brand_font, anchor="mm")
        except:
            pass

        gradient_img.convert("RGB").save(output_path, "JPEG")
        return True

    @classmethod
    def render_subtitle_image(cls, text, font_path, output_path):
        """Renders Vietnamese subtitle text onto a transparent PNG overlay."""
        # Create transparent image
        img = Image.new("RGBA", (cls.VIDEO_WIDTH, cls.VIDEO_HEIGHT), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Wrap text manually
        max_chars_per_line = 32
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            current_line.append(word)
            if len(" ".join(current_line)) > max_chars_per_line:
                current_line.pop()
                lines.append(" ".join(current_line))
                current_line = [word]
        if current_line:
            lines.append(" ".join(current_line))
            
        full_text = "\n".join(lines)
        
        # Load font
        try:
            font = ImageFont.truetype(font_path, 50)
        except Exception as e:
            print(f"Font loading error: {e}. Falling back to default.")
            font = ImageFont.load_default()
            
        # Draw text at the lower third of the video
        text_y = cls.VIDEO_HEIGHT * 0.7
        
        # Calculate text bounding box for background container
        # Use simple estimation since font.getbbox is standard in newer PIL
        try:
            line_heights = []
            max_width = 0
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
                line_heights.append(h)
                if w > max_width:
                    max_width = w
            total_height = sum(line_heights) + (len(lines) - 1) * 15
        except:
            # Fallback box sizes
            max_width = 800
            total_height = len(lines) * 60

        # Draw translucent background box for readability
        box_w = min(max_width + 60, cls.VIDEO_WIDTH - 100)
        box_h = total_height + 40
        box_x = (cls.VIDEO_WIDTH - box_w) // 2
        box_y = text_y - 20
        
        draw.rounded_rectangle(
            [box_x, box_y, box_x + box_w, box_y + box_h], 
            radius=20, 
            fill=(0, 0, 0, 160)
        )
        
        # Draw text centered in the box
        draw.text(
            (cls.VIDEO_WIDTH // 2, text_y + total_height // 2 - 10), 
            full_text, 
            fill=(255, 255, 255, 255), 
            font=font, 
            anchor="mm",
            align="center",
            spacing=15
        )
        
        img.save(output_path, "PNG")

    @classmethod
    def compile_video(cls, script_data, output_video_path):
        """Assembles synthesized audio, visuals, and subtitle images into a finished video."""
        temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_render")
        os.makedirs(temp_dir, exist_ok=True)
        os.makedirs(os.path.dirname(output_video_path), exist_ok=True)

        font_path = cls._download_font_if_needed()
        voice_model = script_data.get("voice_model", "vi-VN-HoaiMyNeural")
        
        clips = []
        audio_clips = []
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            for idx, scene in enumerate(script_data["scenes"]):
                scene_num = scene["scene_number"]
                voiceover = scene["voiceover_text"]
                visual_prompt = scene["visual_prompt"]
                
                # 1. Synthesize audio
                audio_path = os.path.join(temp_dir, f"audio_{scene_num}.mp3")
                print(f"Generating voiceover for Scene {scene_num}...")
                loop.run_until_complete(cls.synthesize_speech(voiceover, voice_model, audio_path))
                
                # 2. Get Visual Assets
                image_path = os.path.join(temp_dir, f"visual_{scene_num}.jpg")
                success = cls.fetch_pexels_image(visual_prompt, image_path)
                if not success:
                    print(f"Pexels download failed for '{visual_prompt}'. Generating fallback gradient.")
                    cls.generate_pastel_background(idx, voiceover, image_path)
                
                # 3. Create Subtitle Overlay
                sub_path = os.path.join(temp_dir, f"sub_{scene_num}.png")
                cls.render_subtitle_image(voiceover, font_path, sub_path)
                
                # 4. Load Clips
                audio_clip = AudioFileClip(audio_path)
                duration = audio_clip.duration
                
                # Add tiny buffer to duration
                duration += 0.2
                
                img_clip = ImageClip(image_path).set_duration(duration)
                sub_clip = ImageClip(sub_path).set_duration(duration)
                
                # Composite scene (image + subtitle overlay)
                scene_clip = CompositeVideoClip([img_clip, sub_clip])
                scene_clip = scene_clip.set_audio(audio_clip)
                
                clips.append(scene_clip)
                audio_clips.append(audio_clip)
            
            # Concatenate all scenes
            final_video = concatenate_videoclips(clips, method="compose")
            
            # Save final compiled video file
            print("Rendering final video compilation...")
            
            # Since VPS does not have a display, we use libx264 codec
            # We also disable log output of moviepy to keep logs clean
            final_video.write_videofile(
                output_video_path,
                fps=24,
                codec="libx264",
                audio_codec="aac",
                verbose=False,
                logger=None
            )
            
            print(f"Video compiled successfully at {output_video_path}")
            return True
            
        except Exception as e:
            print(f"Error compiling video: {e}")
            return False
            
        finally:
            # Clean up audio and temp files
            for c in clips:
                try:
                    c.close()
                except:
                    pass
            for a in audio_clips:
                try:
                    a.close()
                except:
                    pass
            loop.close()
            
            # Try to remove temp files
            for file in os.listdir(temp_dir):
                try:
                    os.remove(os.path.join(temp_dir, file))
                except:
                    pass
            try:
                os.rmdir(temp_dir)
            except:
                pass
