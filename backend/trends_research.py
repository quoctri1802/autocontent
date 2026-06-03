import xml.etree.ElementTree as ET
import httpx
import re
import datetime
import asyncio
import json
import google.generativeai as genai
from db_connector import DBConnector
from config import Config

class TrendsResearcher:
    # Standard keywords in Vietnamese parenting
    PARENTING_KEYWORDS = [
        "trẻ sơ sinh", "bé", "mẹ bầu", "sau sinh", "ăn dặm", "sữa mẹ", "tả", "bỉm",
        "tiêm chủng", "vaccine", "chích ngừa", "ho", "sốt", "tiêu chảy", "biếng ăn",
        "rốn", "vàng da", "tắm bé", "easy", "ngủ ngon", "rèn ngủ", "mọc răng", "khóc đêm"
    ]

    _keywords_pattern = None

    @classmethod
    def _get_keywords_regex(cls):
        if cls._keywords_pattern is None:
            escaped = [re.escape(kw) for kw in cls.PARENTING_KEYWORDS]
            cls._keywords_pattern = re.compile(r'(' + '|'.join(escaped) + r')', re.IGNORECASE)
        return cls._keywords_pattern

    @classmethod
    async def fetch_rss_trends(cls):
        """Fetches latest articles from VnExpress and filters for parenting keywords in parallel."""
        urls = [
            "https://vnexpress.net/rss/gia-dinh.rss",
            "https://vnexpress.net/rss/suc-khoe.rss"
        ]
        
        found_trends = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        keywords_re = cls._get_keywords_regex()
        html_tags_re = re.compile(r'<[^>]*>')

        async with httpx.AsyncClient(headers=headers, timeout=10.0) as client:
            tasks = [client.get(url) for url in urls]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            for response in responses:
                if isinstance(response, Exception) or response.status_code != 200:
                    print(f"RSS fetch warning/error: {response}")
                    continue
                
                try:
                    # Clean encoding declaration if parsing fails
                    xml_text = response.text
                    root = ET.fromstring(xml_text)
                    for item in root.findall(".//item"):
                        title = item.find("title").text or ""
                        description = item.find("description").text or ""
                        
                        clean_desc = html_tags_re.sub('', description)
                        combined_text = f"{title} {clean_desc}"
                        
                        matches = keywords_re.findall(combined_text)
                        
                        if matches:
                            unique_matches = set(m.lower() for m in matches)
                            score = min(40 + len(unique_matches) * 15, 95)
                            found_trends.append({
                                "keyword": title,
                                "source": "VnExpress RSS",
                                "popularity_score": score,
                                "is_viral": True if score > 70 else False,
                                "generated_ideas": f"Phân tích chủ đề: {title}. Gợi ý viết bài về chăm sóc bé dựa trên tin tức này."
                            })
                except Exception as e:
                    print(f"Error parsing RSS XML: {e}")
                    
        return found_trends

    @classmethod
    def get_seasonal_trends(cls):
        """Generates seasonal parenting trends based on the current month."""
        month = datetime.datetime.now().month
        seasonal_ideas = []
        
        if month in [4, 5, 6, 7, 8]: # Summer/Wet season in VN
            seasonal_ideas = [
                {"keyword": "Phòng tránh Tay Chân Miệng ở trẻ em mùa nắng nóng", "score": 90},
                {"keyword": "Cách chăm sóc trẻ bị rôm sảy, mẩn ngứa ngày hè", "score": 85},
                {"keyword": "Bảo quản sữa mẹ mùa hè không lo bị chua, hỏng", "score": 80},
                {"keyword": "Có nên bật điều hòa cho trẻ sơ sinh vào mùa hè?", "score": 92}
            ]
        elif month in [9, 10, 11]: # Fall/Transition season
            seasonal_ideas = [
                {"keyword": "Thời điểm tiêm phòng Cúm mùa hiệu quả nhất cho bé", "score": 88},
                {"keyword": "Cách giữ ấm cổ họng, phòng viêm phế quản khi giao mùa", "score": 85},
                {"keyword": "Bổ sung Vitamin D3 K2 thế nào khi trời ít nắng?", "score": 80}
            ]
        else: # Winter/Spring
            seasonal_ideas = [
                {"keyword": "Phòng ngừa tiêu chảy cấp do Rotavirus mùa đông xuân", "score": 88},
                {"keyword": "Giữ ấm cho bé sơ sinh khi tắm vào mùa lạnh", "score": 95},
                {"keyword": "Trẻ sơ sinh bị ho sổ mũi: Khi nào cần đi bệnh viện?", "score": 90}
            ]
            
        trends = []
        for idea in seasonal_ideas:
            trends.append({
                "keyword": idea["keyword"],
                "source": "Seasonal Engine",
                "popularity_score": idea["score"],
                "is_viral": True if idea["score"] > 85 else False,
                "generated_ideas": f"Chủ đề theo mùa: {idea['keyword']}. Viết bài tư vấn chi tiết cho mẹ bỉm sữa."
            })
        return trends

    @classmethod
    def fetch_social_trends_via_gemini(cls):
        """Uses Gemini API to research and extract current parenting hot trends on social media."""
        if not Config.GEMINI_API_KEY:
            return []
            
        try:
            genai.configure(api_key=Config.GEMINI_API_KEY)
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            prompt = """
Bạn là công cụ "AI Trend Hunter" của cộng đồng 'Mẹ Bỉm Thông Thái'.
Nhiệm vụ của bạn là nghiên cứu và phát hiện các chủ đề, từ khóa, trào lưu, và các cuộc thảo luận đang cực kỳ "hot" (viral) trên các nền tảng mạng xã hội (Facebook, TikTok, Instagram, YouTube Reels) tại Việt Nam liên quan đến các lĩnh vực:
1. Chăm sóc sức khỏe trẻ sơ sinh & trẻ nhỏ (ví dụ: dịch sởi, sốt xuất huyết, tay chân miệng, tiêu chảy, ho sốt, viêm phổi...).
2. Phương pháp nuôi dạy con (giấc ngủ EASY, ăn dặm BLW, ăn dặm kiểu Nhật, rèn tự lập...).
3. Dinh dưỡng & sữa mẹ (kích sữa, tắc sữa, trữ sữa, sữa công thức, thực phẩm bổ sung...).
4. Tâm lý mẹ bầu và mẹ sau sinh (trầm cảm sau sinh, mẹo lấy lại vóc dáng, chăm sóc bản thân...).
5. Trào lưu/thảo luận tranh cãi nóng hổi trên MXH đang được các mẹ bỉm bàn tán xôn xao.

Hãy trả về danh sách gồm 12 chủ đề nóng hổi nhất hiện tại. Mỗi chủ đề phải thực tế, gần gũi với mạng xã hội Việt Nam và có định dạng JSON như sau:
[
  {
    "keyword": "Tên chủ đề/từ khóa hot ngắn gọn, thu hút (ví dụ: 'Trào lưu rèn con tự ngủ theo EASY từ 2 tuần tuổi')",
    "source": "Nguồn phát hiện xu hướng (ví dụ: 'TikTok Trend', 'Facebook Group thảo luận', 'Reels Viral', 'Google Search Trend')",
    "popularity_score": 85,
    "is_viral": true,
    "generated_ideas": "Gợi ý định hướng viết bài viết hoặc làm video ngắn để admin khai thác chủ đề này"
  }
]

Lưu ý: Chỉ trả về JSON thuần túy trong khối ```json ```, không có văn bản giải thích ngoài khối JSON.
"""
            response = model.generate_content(prompt)
            clean_text = response.text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            elif clean_text.startswith("```"):
                clean_text = clean_text[3:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            clean_text = clean_text.strip()
            
            trends_list = json.loads(clean_text)
            if isinstance(trends_list, list):
                return trends_list
        except Exception as e:
            print(f"Error fetching social trends via Gemini: {e}")
        return []

    @classmethod
    async def update_trends_database(cls):
        """Fetches RSS, Gemini social trends, and seasonal trends, then inserts them. Uses per-item transactions to prevent PostgreSQL aborts."""
        # 1. Fetch from Gemini
        gemini_trends = cls.fetch_social_trends_via_gemini()
        
        # 2. Fetch RSS
        rss_trends = []
        try:
            rss_trends = await cls.fetch_rss_trends()
        except Exception as rss_err:
            print(f"Error fetching RSS trends: {rss_err}")
            
        # 3. Fetch Seasonal
        seasonal_trends = cls.get_seasonal_trends()
        
        # Combine trends
        all_trends = gemini_trends + rss_trends + seasonal_trends
        
        if not all_trends:
            all_trends = [
                {
                    "keyword": "Có nên rèn bé ngủ EASY từ sơ sinh?",
                    "source": "Facebook Community",
                    "popularity_score": 90,
                    "is_viral": True,
                    "generated_ideas": "Tập trung giải thích ưu và nhược điểm của rèn ngủ EASY cho bé sơ sinh dưới góc nhìn y khoa khoa học."
                },
                {
                    "keyword": "Ăn dặm tự chỉ huy BLW có gây nghẹn cho trẻ?",
                    "source": "TikTok Trend",
                    "popularity_score": 85,
                    "is_viral": True,
                    "generated_ideas": "Mẹo nhỏ cho mẹ chuẩn bị thức ăn dặm BLW an toàn và cách xử lý hóc dị vật cơ bản."
                }
            ]
        
        conn, cursor_factory = DBConnector.get_connection()
        cursor = conn.cursor()
        is_postgres = DBConnector.get_connection_type() == "postgres"

        insert_count = 0
        for trend in all_trends:
            try:
                keyword = trend.get("keyword", "")[:250]
                source = trend.get("source", "Unknown")[:95]
                popularity_score = int(trend.get("popularity_score", 50))
                is_viral = bool(trend.get("is_viral", False))
                generated_ideas = trend.get("generated_ideas", "")
                
                if is_postgres:
                    cursor.execute("""
                        INSERT INTO trends (keyword, source, popularity_score, is_viral, generated_ideas, analyzed_at)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                        ON CONFLICT (keyword) DO UPDATE 
                        SET popularity_score = EXCLUDED.popularity_score, analyzed_at = NOW()
                    """, (keyword, source, popularity_score, is_viral, generated_ideas))
                else:
                    cursor.execute("""
                        INSERT OR REPLACE INTO trends (keyword, source, popularity_score, is_viral, generated_ideas, analyzed_at)
                        VALUES (?, ?, ?, ?, ?, datetime('now'))
                    """, (keyword, source, popularity_score, is_viral, generated_ideas))
                conn.commit()
                insert_count += 1
            except Exception as e:
                print(f"Error inserting trend '{trend.get('keyword', '')}': {e}")
                conn.rollback()
                
        conn.close()
        return insert_count

    @classmethod
    def get_latest_trends(cls, limit=10):
        """Retrieves latest trends from database."""
        query = f"SELECT * FROM trends ORDER BY popularity_score DESC, analyzed_at DESC LIMIT {limit}"
        return DBConnector.execute_query(query)
