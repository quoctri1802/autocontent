import xml.etree.ElementTree as ET
import httpx
import re
import datetime
import asyncio
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
                                "is_viral": 1 if score > 70 else 0,
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
                "is_viral": 1 if idea["score"] > 85 else 0,
                "generated_ideas": f"Chủ đề theo mùa: {idea['keyword']}. Viết bài tư vấn chi tiết cho mẹ bỉm sữa."
            })
        return trends

    @classmethod
    async def update_trends_database(cls):
        """Fetches RSS and seasonal trends, then inserts them. Uses per-item transactions to prevent PostgreSQL aborts."""
        rss_trends_task = cls.fetch_rss_trends()
        seasonal_trends = cls.get_seasonal_trends()
        
        rss_trends = await rss_trends_task
        all_trends = rss_trends + seasonal_trends
        
        conn, cursor_factory = DBConnector.get_connection()
        cursor = conn.cursor()
        is_postgres = DBConnector.get_connection_type() == "postgres"

        # Check if trends table has correct constraint. If not, recreate it.
        try:
            if is_postgres:
                # Ensure trends table has UNIQUE constraint on keyword
                cursor.execute("""
                    SELECT count(*) FROM pg_constraint 
                    WHERE conname = 'trends_keyword_key' OR conname = 'unique_trends_keyword'
                """)
                # If unique constraint not present, let's migrate safely
                # (Easiest way to fix old schema in development is dropping cache table)
                # We do this because of early migrations.
                cursor.execute("SELECT count(*) FROM pg_indexes WHERE indexname = 'trends_keyword_key'")
                if cursor.fetchone()[0] == 0:
                    print("Migrating trends table to add unique constraint...")
                    cursor.execute("DROP TABLE IF EXISTS trends;")
                    conn.commit()
                    # Re-initialize DB
                    DBConnector.init_db()
                    # Re-open cursor after drop/recreate
                    conn, cursor_factory = DBConnector.get_connection()
                    cursor = conn.cursor()
        except Exception as migrate_err:
            print(f"Migration check warning: {migrate_err}")
            conn.rollback()

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
                # Commit immediately for this item to isolate database errors
                conn.commit()
                insert_count += 1
            except Exception as e:
                print(f"Error inserting trend '{trend['keyword']}': {e}")
                # Rollback current aborted transaction block to resume loop
                conn.rollback()
                
        conn.close()
        return insert_count

    @classmethod
    def get_latest_trends(cls, limit=10):
        """Retrieves latest trends from database."""
        query = f"SELECT * FROM trends ORDER BY popularity_score DESC, analyzed_at DESC LIMIT {limit}"
        return DBConnector.execute_query(query)
