"""
写入演示账号 demo / Demo@123456
用法（需先开 SSH 隧道）:
  ssh -L 3306:127.0.0.1:3306 root@120.26.72.29
  .\\.venv\\Scripts\\python.exe scripts\\seed_demo_user.py
"""
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.database.mysql import SessionLocal
from app.models.user import User

DEMO_USERNAME = "demo"
DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "Demo@123456"


def main() -> None:
    db: Session = SessionLocal()
    try:
        existing = (
            db.query(User)
            .filter((User.username == DEMO_USERNAME) | (User.email == DEMO_EMAIL))
            .first()
        )
        if existing:
            existing.password_hash = hash_password(DEMO_PASSWORD)
            existing.username = DEMO_USERNAME
            existing.email = DEMO_EMAIL
            db.commit()
            print(f"已更新演示账号: {DEMO_USERNAME} / {DEMO_PASSWORD}")
            return

        user = User(
            username=DEMO_USERNAME,
            email=DEMO_EMAIL,
            password_hash=hash_password(DEMO_PASSWORD),
        )
        db.add(user)
        db.commit()
        print(f"已创建演示账号: {DEMO_USERNAME} / {DEMO_PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
