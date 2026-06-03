import os
import sqlite3
import urllib.parse as urlparse
import psycopg2
from psycopg2.extras import RealDictCursor
from config import Config

class DBConnector:
    _connection_type = "sqlite"

    @classmethod
    def get_connection(cls):
        """Returns a database connection and its cursor type."""
        db_url = Config.DATABASE_URL
        if db_url and db_url.startswith("postgresql"):
            try:
                # Test connection
                conn = psycopg2.connect(db_url)
                cls._connection_type = "postgres"
                return conn, RealDictCursor
            except Exception as e:
                print(f"Warning: Failed to connect to PostgreSQL ({e}). Falling back to SQLite.")
        
        # SQLite Fallback
        cls._connection_type = "sqlite"
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(__file__)), exist_ok=True)
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mbte_local.db")
        conn = sqlite3.connect(db_path)
        # Enable dictionary-like row access for SQLite
        conn.row_factory = sqlite3.Row
        return conn, None

    @classmethod
    def get_connection_type(cls):
        return cls._connection_type

    @classmethod
    def execute_query(cls, query, params=None, fetch="all"):
        """Utility function to execute queries safely."""
        conn, cursor_factory = cls.get_connection()
        try:
            if cursor_factory:
                # Postgres
                with conn.cursor(cursor_factory=cursor_factory) as cursor:
                    cursor.execute(query, params or ())
                    normalized_query = query.strip().upper()
                    if normalized_query.startswith("SELECT") or "RETURNING" in normalized_query:
                        result = cursor.fetchall()
                        conn.commit()
                        return [dict(row) for row in result]
                    conn.commit()
                    return []
            else:
                # SQLite
                cursor = conn.cursor()
                cursor.execute(query, params or ())
                if query.strip().upper().startswith("SELECT"):
                    result = cursor.fetchall()
                    conn.commit()
                    return [dict(row) for row in result]
                elif query.strip().upper().startswith("INSERT"):
                    # For sqlite insert, get the last row id
                    last_row_id = cursor.lastrowid
                    conn.commit()
                    return [{"id": last_row_id}]
                conn.commit()
                return []
        except Exception as e:
            print(f"Database query error: {e}\nQuery: {query}")
            try:
                conn.rollback()
            except:
                pass
            raise e
        finally:
            conn.close()

    @classmethod
    def init_db(cls):
        """Initializes tables in the database."""
        conn, _ = cls.get_connection()
        cursor = conn.cursor()

        is_postgres = cls._connection_type == "postgres"
        
        # Schema migration check: Drop trends table if it lacks the UNIQUE constraint
        if is_postgres:
            try:
                cursor.execute("""
                    SELECT COUNT(*) FROM information_schema.table_constraints 
                    WHERE table_name='trends' AND constraint_type='UNIQUE'
                """)
                res = cursor.fetchone()
                if res and res[0] == 0:
                    # Table exists but lacks UNIQUE constraint. Drop to recreate.
                    print("PostgreSQL 'trends' table lacks UNIQUE constraint. Dropping to migrate...")
                    cursor.execute("DROP TABLE IF EXISTS trends CASCADE")
                    conn.commit()
            except Exception as migrate_err:
                print(f"Trends schema check skipped/warning: {migrate_err}")
                conn.rollback()

        serial_type = "SERIAL PRIMARY KEY" if is_postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"
        timestamp_type = "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
        text_type = "TEXT"
        boolean_type = "BOOLEAN"

        # 1. Articles table (Website)
        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS articles (
            id {serial_type},
            title VARCHAR(255) NOT NULL,
            content {text_type} NOT NULL,
            summary {text_type},
            category VARCHAR(100),
            subcategory VARCHAR(100),
            tags VARCHAR(255),
            status VARCHAR(50) DEFAULT 'draft',
            meta_title VARCHAR(255),
            meta_description {text_type},
            author VARCHAR(100) DEFAULT 'Bác sĩ Hải Anh',
            created_at {timestamp_type},
            scheduled_at TIMESTAMP,
            published_at TIMESTAMP
        )
        """)

        # 2. Facebook Posts table
        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS facebook_posts (
            id {serial_type},
            content {text_type} NOT NULL,
            image_url VARCHAR(512),
            status VARCHAR(50) DEFAULT 'draft',
            fb_post_id VARCHAR(100),
            created_at {timestamp_type},
            published_at TIMESTAMP
        )
        """)

        # 3. Video Scripts table (TikTok, Reels, Shorts)
        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS video_scripts (
            id {serial_type},
            title VARCHAR(255) NOT NULL,
            hook VARCHAR(255),
            voiceover_text {text_type} NOT NULL,
            visual_prompts {text_type},
            bg_music VARCHAR(100) DEFAULT 'lullaby',
            voice_model VARCHAR(100) DEFAULT 'vi-VN-HoaiMyNeural',
            status VARCHAR(50) DEFAULT 'draft',
            video_path VARCHAR(512),
            tiktok_published {boolean_type} DEFAULT FALSE,
            facebook_published {boolean_type} DEFAULT FALSE,
            youtube_published {boolean_type} DEFAULT FALSE,
            created_at {timestamp_type},
            scheduled_at TIMESTAMP
        )
        """)

        # 4. Trends table
        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS trends (
            id {serial_type},
            keyword VARCHAR(255) UNIQUE NOT NULL,
            source VARCHAR(100),
            popularity_score INTEGER DEFAULT 50,
            analyzed_at {timestamp_type},
            is_viral {boolean_type} DEFAULT FALSE,
            generated_ideas {text_type}
        )
        """)

        # 5. System Settings table
        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS system_settings (
            key VARCHAR(100) PRIMARY KEY,
            value {text_type}
        )
        """)

        # Insert some initial settings if empty
        try:
            cursor.execute("SELECT COUNT(*) FROM system_settings")
            count = cursor.fetchone()[0]
            if count == 0:
                settings = [
                    ('default_voice', 'vi-VN-HoaiMyNeural'),
                    ('default_hashtags', '#mebimthongthai #nuoiconkhoahoc #easyroutine'),
                    ('post_frequency_days', '1'),
                    ('video_duration_max', '60')
                ]
                for key, val in settings:
                    cursor.execute("INSERT INTO system_settings (key, value) VALUES (?, ?)" if not is_postgres else "INSERT INTO system_settings (key, value) VALUES (%s, %s)", (key, val))
        except Exception as ex:
            print(f"Error seeding settings: {ex}")

        # Check and add missing columns for existing tables
        migrations = [
            ("articles", "subcategory", "VARCHAR(100)"),
            ("articles", "meta_title", "VARCHAR(255)"),
            ("articles", "meta_description", text_type),
            ("articles", "author", "VARCHAR(100) DEFAULT 'Bác sĩ Hải Anh'"),
            ("articles", "scheduled_at", "TIMESTAMP"),
            ("articles", "published_at", "TIMESTAMP"),
            
            ("facebook_posts", "image_url", "VARCHAR(512)"),
            ("facebook_posts", "fb_post_id", "VARCHAR(100)"),
            ("facebook_posts", "published_at", "TIMESTAMP"),
            
            ("video_scripts", "hook", "VARCHAR(255)"),
            ("video_scripts", "visual_prompts", text_type),
            ("video_scripts", "bg_music", "VARCHAR(100) DEFAULT 'lullaby'"),
            ("video_scripts", "voice_model", "VARCHAR(100) DEFAULT 'vi-VN-HoaiMyNeural'"),
            ("video_scripts", "video_path", "VARCHAR(512)"),
            ("video_scripts", "tiktok_published", f"{boolean_type} DEFAULT FALSE"),
            ("video_scripts", "facebook_published", f"{boolean_type} DEFAULT FALSE"),
            ("video_scripts", "youtube_published", f"{boolean_type} DEFAULT FALSE"),
            ("video_scripts", "scheduled_at", "TIMESTAMP"),
            
            ("trends", "is_viral", f"{boolean_type} DEFAULT FALSE"),
            ("trends", "generated_ideas", text_type)
        ]
        
        for table, column, col_type in migrations:
            try:
                if is_postgres:
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {col_type}")
                else:
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
                conn.commit()
            except Exception as alter_err:
                if is_postgres:
                    print(f"Postgres column migration warning: {column} in {table}: {alter_err}")
                try:
                    conn.rollback()
                except:
                    pass

        conn.commit()
        conn.close()
        print(f"Database initialized successfully with {cls._connection_type.upper()}!")

# Initialize DB on import
try:
    DBConnector.init_db()
except Exception as e:
    print(f"Error initializing DB: {e}")
