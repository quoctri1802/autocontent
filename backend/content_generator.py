import json
import re
import google.generativeai as genai
from config import Config

class ContentGenerator:
    _configured = False

    @classmethod
    def _configure_gemini(cls):
        if not cls._configured:
            if Config.GEMINI_API_KEY:
                try:
                    genai.configure(api_key=Config.GEMINI_API_KEY)
                    cls._configured = True
                except Exception as e:
                    print(f"Error configuring Gemini API: {e}")
            else:
                print("Warning: GEMINI_API_KEY is not set. Using mock content generator fallback.")

    @classmethod
    def _clean_json_response(cls, text):
        """Cleans markdown JSON block markings from Gemini response."""
        clean_text = text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        elif clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        return clean_text.strip()

    @classmethod
    def generate_article(cls, topic):
        """Generates a long-form SEO blog article from a topic."""
        cls._configure_gemini()
        
        if not cls._configured:
            return cls._mock_article(topic)

        prompt = f"""
Bạn là chuyên gia bác sĩ nhi khoa và chuyên gia tư vấn nuôi con sữa mẹ & rèn ngủ EASY cho cộng đồng 'Mẹ Bỉm Thông Thái'.
Hãy viết một bài viết SEO học thuật, giàu kiến thức nhưng dễ hiểu, ấm áp cho chủ đề: "{topic}".

Hãy trả về kết quả dưới định dạng JSON duy nhất với cấu trúc sau:
{{
  "title": "Tiêu đề bài viết thu hút, chuẩn SEO (khoảng 60-70 ký tự)",
  "summary": "Tóm tắt ngắn gọn của bài viết (khoảng 150 ký tự)",
  "content": "Nội dung bài viết chi tiết, định dạng bằng mã HTML sạch (sử dụng các thẻ h2, h3, p, ul, li, strong). Hãy viết chi tiết, khoa học, độ dài khoảng 800 - 1200 từ.",
  "category": "Chọn một trong các mục: Mang thai, Sơ sinh, Nuôi dạy, Dinh dưỡng, Chăm sóc bé",
  "subcategory": "Danh mục con tương ứng (ví dụ: Giấc ngủ EASY, Ăn dặm dặm BLW, Vắc xin)",
  "tags": "Từ khóa cách nhau bởi dấu phẩy",
  "meta_title": "Tiêu đề hiển thị trên Google",
  "meta_description": "Mô tả SEO thu hút nhấp chuột"
}}

Lưu ý: Chỉ trả về JSON thuần túy, không có văn bản giải thích ngoài khối JSON.
"""
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            json_text = cls._clean_json_response(response.text)
            return json.loads(json_text)
        except Exception as e:
            print(f"Error generating article via Gemini: {e}")
            return cls._mock_article(topic)

    @classmethod
    def generate_facebook_post(cls, topic, article_content=None):
        """Generates an engaging Facebook post for a topic, optionally utilizing article details."""
        cls._configure_gemini()
        
        if not cls._configured:
            return cls._mock_facebook_post(topic)

        article_context = f"\nDựa trên bài viết này:\n{article_content}" if article_content else ""
        
        prompt = f"""
Bạn là Admin của trang Facebook 'Mẹ Bỉm Thông Thái Đà Nẵng'. Hãy viết một bài viết đăng Facebook cực kỳ thu hút, gần gũi, dùng nhiều biểu tượng cảm xúc (emojis), có văn phong chia sẻ, tâm sự của mẹ bỉm nhưng thông thái và khoa học về chủ đề: "{topic}".
{article_context}

Hãy trả về kết quả dưới định dạng JSON duy nhất với cấu trúc sau:
{{
  "content": "Nội dung bài viết Facebook. Gồm: 1 hook giật gân/tò mò, 3-4 gạch đầu dòng chia sẻ cốt lõi ngắn gọn dễ nhớ, lời kêu gọi hành động (Call To Action) tương tác hoặc truy cập web, và 5-6 hashtags liên quan.",
  "suggested_image_prompt": "Mô tả một bức ảnh đẹp, ấm áp để thiết kế hoặc tìm kiếm trên mạng phù hợp bài viết này"
}}

Lưu ý: Chỉ trả về JSON thuần túy, không có văn bản giải thích.
"""
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            json_text = cls._clean_json_response(response.text)
            return json.loads(json_text)
        except Exception as e:
            print(f"Error generating FB post via Gemini: {e}")
            return cls._mock_facebook_post(topic)

    @classmethod
    def generate_video_script(cls, topic):
        """Generates a structured short-video script (scenes under 60 seconds)."""
        cls._configure_gemini()
        
        if not cls._configured:
            return cls._mock_video_script(topic)

        prompt = f"""
Bạn là nhà sáng tạo nội dung video ngắn triệu view (TikTok/Reels). Hãy viết một kịch bản video ngắn dưới 60 giây chia sẻ mẹo nuôi con cho chủ đề: "{topic}".
Kịch bản cần có câu mở đầu cuốn hút (hook) trong 3 giây đầu, lời thoại ngắn gọn, tốc độ đọc vừa phải, xúc tích.

Hãy trả về kết quả dưới định dạng JSON duy nhất với cấu trúc sau:
{{
  "title": "Tiêu đề kịch bản video",
  "hook": "Câu thoại mở đầu thu hút sự chú ý trong 3 giây đầu",
  "bg_music": "Chọn phong cách nhạc nền: happy, lullaby, emotional, energetic",
  "voice_model": "Chọn một giọng đọc: vi-VN-HoaiMyNeural (Giọng nữ Nam) hoặc vi-VN-NamMinhNeural (Giọng nam Bắc)",
  "scenes": [
    {{
      "scene_number": 1,
      "voiceover_text": "Lời thoại thoại tiếng Việt sẽ được đọc lên trong phân cảnh này (khoảng 15-20 từ)",
      "visual_prompt": "Từ khóa tìm kiếm bằng tiếng Anh để tìm video/ảnh nền trên Pexels phù hợp cảnh này (ví dụ: 'sleeping baby close up', 'crying baby', 'mother breastfeeding')",
      "duration_seconds": 5
    }}
  ]
}}

Lưu ý: 
1. Tổng số giây (duration_seconds) của tất cả các cảnh cộng lại phải từ 30 đến 55 giây.
2. Chỉ trả về JSON thuần túy, không thêm bất kỳ văn bản nào bên ngoài.
"""
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            json_text = cls._clean_json_response(response.text)
            script_data = json.loads(json_text)
            # Validate JSON schema matches expected video script structure
            if not isinstance(script_data, dict) or "scenes" not in script_data or not isinstance(script_data["scenes"], list) or len(script_data["scenes"]) == 0:
                raise ValueError("Invalid script schema returned by Gemini API.")
            return script_data
        except Exception as e:
            print(f"Error generating video script via Gemini: {e}")
            return cls._mock_video_script(topic)

    # --- FALLBACK MOCK DATA GENERATORS FOR TESTING WITHOUT API KEYS ---
    @classmethod
    def _mock_article(cls, topic):
        return {
            "title": f"Cẩm Nang Chăm Bé: {topic} Đúng Cách Chuẩn Khoa Học",
            "summary": f"Bài viết hướng dẫn chi tiết mẹ cách xử lý và chăm sóc bé khi gặp tình trạng {topic} giúp mẹ nuôi con nhàn tênh.",
            "content": f"""
            <h2>Hiểu đúng về {topic} ở trẻ nhỏ</h2>
            <p>Tình trạng <strong>{topic}</strong> là vấn đề vô cùng phổ biến ở trẻ nhỏ, đặc biệt là giai đoạn dưới 1 tuổi. Nhiều mẹ bỉm sữa thường rất lo lắng và vội vàng áp dụng các bài thuốc truyền miệng chưa được kiểm chứng.</p>
            
            <h2>3 Nguyên tắc vàng khi chăm sóc bé</h2>
            <ul>
                <li><strong>Giữ vệ sinh sạch sẽ:</strong> Đây là yếu tố cốt lõi giúp ngăn ngừa vi khuẩn xâm nhập sâu hơn.</li>
                <li><strong>Theo dõi sát sao:</strong> Mẹ cần ghi chép lịch sinh hoạt, ăn ngủ của bé để nhận diện dấu hiệu bất thường.</li>
                <li><strong>Bổ sung dinh dưỡng khoa học:</strong> Tiếp tục cho bé bú mẹ hoàn toàn hoặc chia nhỏ các bữa ăn dặm.</li>
            </ul>

            <h2>Khi nào mẹ cần đưa bé đi gặp bác sĩ nhi khoa?</h2>
            <p>Mẹ không nên tự ý mua thuốc kháng sinh. Hãy đưa bé đi khám ngay nếu bé có các dấu hiệu như sốt cao liên tục trên 38.5 độ, lờ đờ, bỏ bú, hoặc khóc thét không dứt.</p>
            """,
            "category": "Chăm sóc bé",
            "subcategory": "Sức khỏe y khoa",
            "tags": f"chăm sóc bé, {topic}, nuôi con khoa học, mẹ bỉm thông thái",
            "meta_title": f"Cách chăm sóc bé bị {topic} chuẩn khoa học | Mẹ Bỉm Thông Thái",
            "meta_description": f"Mách mẹ bỉm sữa cách xử lý thông thái tại nhà khi bé bị {topic} cực kỳ hiệu quả, an toàn."
        }

    @classmethod
    def _mock_facebook_post(cls, topic):
        return {
            "content": f"""🚨 MẸ CÓ BIẾT: XỬ LÝ {topic.upper()} THẾ NÀO MỚI ĐÚNG? 🚨

🍼 Nhiều mẹ nhắn tin cho page hỏi về vấn đề {topic}, lo lắng đứng ngồi không yên vì con quấy khóc. Đừng lo mẹ ơi, lưu ngay 3 mẹo khoa học này nha:

1️⃣ Bình tĩnh theo dõi các biểu hiện của bé, tránh tự ý mua thuốc kháng sinh.
2️⃣ Giữ môi trường xung quanh bé sạch sẽ, thông thoáng.
3️⃣ Tăng cường cho bé bú mẹ hoặc uống nước ấm (nếu bé trên 6 tháng).

👉 Chi tiết hướng dẫn y khoa mẹ xem tại bài viết mới nhất trên Website của Mẹ Bỉm Thông Thái nha!

#mebimthongthai #mebimdanang #nuoiconkhoahoc #chamsocbe #{topic.replace(' ', '')}""",
            "suggested_image_prompt": "A warm photo of a Vietnamese mother gently holding and smiling at her healthy, happy baby in a cozy bright room."
        }

    @classmethod
    def _mock_video_script(cls, topic):
        return {
            "title": f"Mẹo xử lý {topic} cực nhàn",
            "hook": f"Con bị {topic} mẹ chớ lo lắng, làm ngay 3 bước này nhé!",
            "bg_music": "lullaby",
            "voice_model": "vi-VN-HoaiMyNeural",
            "scenes": [
                {
                    "scene_number": 1,
                    "voiceover_text": f"Chào các mẹ! Hôm nay mình sẽ chia sẻ mẹo xử lý {topic} cực kỳ đơn giản tại nhà.",
                    "visual_prompt": "smiling vietnamese mother playing with baby",
                    "duration_seconds": 6
                },
                {
                    "scene_number": 2,
                    "voiceover_text": "Bước một, mẹ cần giữ vệ sinh cho bé sạch sẽ và giữ phòng bé luôn thông thoáng mát mẻ.",
                    "visual_prompt": "bright clean baby bedroom nursery interior",
                    "duration_seconds": 6
                },
                {
                    "scene_number": 3,
                    "voiceover_text": "Bước hai, hãy chia nhỏ cữ bú hoặc bữa ăn dặm để con hấp thu tốt hơn mà không bị quá tải.",
                    "visual_prompt": "mother feeding baby milk bottle close up",
                    "duration_seconds": 7
                },
                {
                    "scene_number": 4,
                    "voiceover_text": "Cuối cùng, nếu bé có biểu hiện sốt cao hay lờ đờ, mẹ cần đưa bé đi khám bác sĩ ngay nhé.",
                    "visual_prompt": "doctor checking baby heartbeat close up",
                    "duration_seconds": 6
                }
            ]
        }
