import xml.etree.ElementTree as ET
import httpx
import re
import datetime
from db_connector import DBConnector
from config import Config

class TrendsResearcher:
    # Standard keywords in Vietnamese parenting
    PARENTING_KEYWORDS = [
        "trẻ sơ sinh", "bé", "mẹ bầu", "sau sinh", "ăn dặm", "sữa mẹ", "tả", "bỉm",
        "tiêm chủng", "vaccine", "chích ngừa", "ho", "sốt", "tiêu chảy", "biếng ăn",
        "rốn", "vàng da", "tắm bé", "easy", "ngủ ngon", "rèn ngủ", "mọc răng", "khóc đêm"
    ]

    @classmethod
    def fetch_rss_trends(cls):
        """Fetches latest articles from VnExpress and filters for parenting keywords."""
        urls = [
            "https://vnexpress.net/rss/gia-dinh.rss",
            "https://vnexpress.net/rss/suc-khoe.rss"
        ]
        
        found_trends = []
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        with httpx.Client(headers=headers, timeout=10.0) as client:
            for url in urls:
                try:
                    response = client.get(url)
                    if response.status_code != 200:
                        continue
                    
                    root = ET.fromstring(response.text)
                    for item in root.findall(".//item"):
                        title = item.find("title").text or ""
                        description = item.find("description").text or ""
                        link = item.find("link").text or ""
                        
                        # Clean description HTML tags
                        clean_desc = re.sub(r'<[^>]*>', '', description)
                        
                        # Match parenting keywords
                        matched_words = [kw for kw in cls.PARENTING_KEYWORDS if kw in title.lower() or kw in clean_desc.lower()]
                        
                        if matched_words:
                            # Calculate popularity score based on keyword density
                            score = min(40 + len(matched_words) * 15, 95)
                            found_trends.append({
                                "keyword": title,
                                "source": "VnExpress RSS",
                                "popularity_score": score,
                                "is_viral": 1 if score > 70 else 0,
                                "generated_ideas": f"Phân tích chủ đề: {title}. Gợi ý viết bài về chăm sóc bé dựa trên tin tức này."
                            })
                except Exception as e:
                    print(f"Error reading RSS {url}: {e}")
                    
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
                "is_viral": 1 if idea["score"] > 85 else 0,
                "generated_ideas": f"Chủ đề theo mùa: {idea['keyword']}. Viết bài tư vấn chi tiết cho mẹ bỉm sữa."
            })
        return trends

    @classmethod
    def update_trends_database(cls):
        """Fetches RSS and seasonal trends, then inserts them into the DB."""
        rss_trends = cls.fetch_rss_trends()
        seasonal_trends = cls.get_seasonal_trends()
        
        all_trends = rss_trends + seasonal_trends
        
        # Insert or ignore (using REPLACE or INSERT ON CONFLICT)
        conn, cursor_factory = DBConnector.get_connection()
        cursor = conn.cursor()
        is_postgres = DBConnector.get_connection_type() == "postgres"

        insert_count = 0
        for trend in all_trends:
            try:
                if is_postgres:
                    cursor.execute("""
                        INSERT INTO trends (keyword, source, popularity_score, is_viral, generated_ideas, analyzed_at)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                        ON CONFLICT (keyword) DO UPDATE 
                        SET popularity_score = EXCLUDED.popularity_score, analyzed_at = NOW()
                    """, (trend["keyword"], trend["source"], trend["popularity_score"], trend["is_viral"], trend["generated_ideas"]))
                else:
                    cursor.execute("""
                        INSERT OR REPLACE INTO trends (keyword, source, popularity_score, is_viral, generated_ideas, analyzed_at)
                        VALUES (?, ?, ?, ?, ?, datetime('now'))
                    """, (trend["keyword"], trend["source"], trend["popularity_score"], trend["is_viral"], trend["generated_ideas"]))
                insert_count += 1
            except Exception as e:
                print(f"Error inserting trend {trend['keyword']}: {e}")
                
        conn.commit()
        conn.close()
        return insert_count

    @classmethod
    def get_latest_trends(cls, limit=10):
        """Retrieves latest trends from database."""
        query = f"SELECT * FROM trends ORDER BY popularity_score DESC, analyzed_at DESC LIMIT {limit}"
        return DBConnector.execute_query(query)
