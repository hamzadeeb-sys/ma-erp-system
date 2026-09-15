import bcrypt
from core.db import get_db_cursor

def verify_password(plain_pwd: str, stored_pwd: str) -> bool:
    if stored_pwd.startswith("$2b$") or stored_pwd.startswith("$2a$"):
        return bcrypt.checkpw(plain_pwd.encode('utf-8'), stored_pwd.encode('utf-8'))
    return plain_pwd == stored_pwd

def hash_password(plain_pwd: str) -> str:
    return bcrypt.hashpw(plain_pwd.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def authenticate_user(username: str, password: str):
    with get_db_cursor(commit=True) as (cur, _):
        cur.execute("""
            SELECT id, username, full_name, role, stakeholder_id, COALESCE(is_active, TRUE), password
            FROM app_users 
            WHERE username = %s;
        """, (username.strip(),))
        user = cur.fetchone()
        if user and verify_password(password.strip(), user[6]):
            # ترقية كلمة المرور تلقائياً إلى تشفير bcrypt
            if not (user[6].startswith("$2b$") or user[6].startswith("$2a$")):
                new_h = hash_password(password.strip())
                cur.execute("UPDATE app_users SET password = %s WHERE id = %s;", (new_h, user[0]))
            return {
                "id": user[0],
                "username": user[1],
                "full_name": user[2],
                "role": user[3],
                "stakeholder_id": user[4],
                "is_active": user[5]
            }
    return None
