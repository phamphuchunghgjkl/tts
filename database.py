import mysql.connector
import uuid
import datetime
import yaml # Mới
from pathlib import Path
from yaml.loader import SafeLoader

# Tải cấu hình từ file config.yaml
with open('config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

MYSQL_CONFIG = config['mysql']

def get_db_connection():
    """Tạo kết nối mới tới database MySQL."""
    try:
        conn = mysql.connector.connect(
            host=MYSQL_CONFIG['host'],
            user=MYSQL_CONFIG['user'],
            password=MYSQL_CONFIG['password'],
            database=MYSQL_CONFIG['database']
        )
        return conn
    except mysql.connector.Error as err:
        print(f"Lỗi kết nối MySQL: {err}")
        return None

# --- Hết Cấu hình ---

def init_db():
    """Khởi tạo bảng trong MySQL nếu chưa tồn tại."""
    conn = get_db_connection()
    if not conn:
        return
    
    cursor = conn.cursor()
    # Câu lệnh SQL này tương thích với cả SQLite và MySQL
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS history (
        id VARCHAR(36) PRIMARY KEY,
        username VARCHAR(255) NOT NULL,
        text TEXT,
        lang VARCHAR(10),
        voice_path TEXT,
        output_path TEXT,
        created_at VARCHAR(50),
        INDEX(username)
    )
    """)
    # Tạo bảng users để lưu trữ tài khoản (username và password hash)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id VARCHAR(36) PRIMARY KEY,
        username VARCHAR(255) NOT NULL UNIQUE,
        password VARCHAR(255) NOT NULL,
        first_name VARCHAR(255),
        last_name VARCHAR(255),
        email VARCHAR(255),
        created_at VARCHAR(50),
        INDEX(username)
    )
    """)
    conn.commit()
    cursor.close()
    conn.close()


def add_user(username: str, password_hash: str, first_name: str = None, last_name: str = None, email: str = None):
    """Thêm user mới vào bảng users."""
    conn = get_db_connection()
    if not conn:
        return False
    cursor = conn.cursor()
    uid = str(uuid.uuid4())
    created_at = datetime.datetime.now().isoformat(timespec="seconds")
    sql = """
    INSERT INTO users (id, username, password, first_name, last_name, email, created_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    try:
        cursor.execute(sql, (uid, username, password_hash, first_name, last_name, email, created_at))
        conn.commit()
        return True
    except mysql.connector.Error as err:
        print(f"Lỗi khi INSERT user: {err}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()


def get_user(username: str):
    """Lấy user theo username, trả về dict hoặc None."""
    conn = get_db_connection()
    if not conn:
        return None
    cursor = conn.cursor(dictionary=True)
    sql = "SELECT * FROM users WHERE username = %s"
    try:
        cursor.execute(sql, (username,))
        user = cursor.fetchone()
        return user
    except mysql.connector.Error as err:
        print(f"Lỗi khi SELECT user: {err}")
        return None
    finally:
        cursor.close()
        conn.close()


def list_users() -> list:
    """Trả về danh sách tất cả người dùng trong bảng users dưới dạng list[dict]."""
    conn = get_db_connection()
    if not conn:
        return []
    cursor = conn.cursor(dictionary=True)
    sql = "SELECT * FROM users ORDER BY created_at ASC"
    try:
        cursor.execute(sql)
        rows = cursor.fetchall()
        return rows
    except mysql.connector.Error as err:
        print(f"Lỗi khi liệt kê users: {err}")
        return []
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    # When run directly, create tables
    print('Initializing database tables...')
    init_db()
    print('Done.')

def add_history_item(username: str, text: str, lang: str, voice_path: str, output_path: str):
    """Thêm một mục lịch sử mới cho user vào MySQL."""
    conn = get_db_connection()
    if not conn:
        return
    
    cursor = conn.cursor()
    item = {
        "id": str(uuid.uuid4()),
        "username": username,
        "text": text,
        "lang": lang,
        "voice_path": str(voice_path),
        "output_path": str(output_path),
        "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    
    sql = """
    INSERT INTO history (id, username, text, lang, voice_path, output_path, created_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    # MySQL connector dùng %s làm placeholder
    values = (
        item["id"], item["username"], item["text"], item["lang"],
        item["voice_path"], item["output_path"], item["created_at"]
    )
    
    try:
        cursor.execute(sql, values)
        conn.commit()
    except mysql.connector.Error as err:
        print(f"Lỗi khi INSERT: {err}")
        conn.rollback() # Hoàn tác nếu có lỗi
    finally:
        cursor.close()
        conn.close()

def load_history(username: str) -> list:
    """Tải lịch sử của user từ MySQL."""
    conn = get_db_connection()
    if not conn:
        return []
    
    # dictionary=True là rất quan trọng!
    # Nó giúp trả về kết quả dạng dict, giống hệt sqlite3.Row
    # Do đó app.py không cần thay đổi
    cursor = conn.cursor(dictionary=True) 
    
    sql = "SELECT * FROM history WHERE username = %s ORDER BY created_at DESC"
    
    try:
        cursor.execute(sql, (username,))
        items = cursor.fetchall()
        return items
    except mysql.connector.Error as err:
        print(f"Lỗi khi SELECT: {err}")
        return []
    finally:
        cursor.close()
        conn.close()

def delete_history_item(username: str, item_id: str):
    """Xoá một mục lịch sử của user trong MySQL."""
    conn = get_db_connection()
    if not conn:
        return

    try:
        # Lấy đường dẫn file để xoá file vật lý
        cursor_select = conn.cursor(dictionary=True)
        sql_select = "SELECT voice_path, output_path FROM history WHERE id = %s AND username = %s"
        cursor_select.execute(sql_select, (item_id, username))
        result = cursor_select.fetchone()
        cursor_select.close()

        if result:
            # Xoá file vật lý
            if Path(result["output_path"]).exists():
                try: Path(result["output_path"]).unlink()
                except Exception: pass
            if Path(result["voice_path"]).exists():
                try: Path(result["voice_path"]).unlink()
                except Exception: pass
        
        # Xoá record khỏi database
        cursor_delete = conn.cursor()
        sql_delete = "DELETE FROM history WHERE id = %s AND username = %s"
        cursor_delete.execute(sql_delete, (item_id, username))
        conn.commit()
        cursor_delete.close()

    except mysql.connector.Error as err:
        print(f"Lỗi khi DELETE: {err}")
        conn.rollback()
    finally:
        conn.close()

def get_history_item(item_id: str) -> dict:
    """Lấy một mục lịch sử cụ thể bằng ID (dùng cho chức năng Sửa)."""
    conn = get_db_connection()
    if not conn:
        return None
        
    cursor = conn.cursor(dictionary=True)
    sql = "SELECT * FROM history WHERE id = %s"
    
    try:
        cursor.execute(sql, (item_id,))
        item = cursor.fetchone()
        return item if item else None
    except mysql.connector.Error as err:
        print(f"Lỗi khi GET: {err}")
        return None
    finally:
        cursor.close()
        conn.close()