from flask import Flask

from . import db
from .models import User, Department


def register_cli(app: Flask) -> None:
    @app.cli.command("seed")
    def seed():
        users = [
            ("gifts", Department.GIFTS),
            ("stationery", Department.STATIONERY),
            ("toys", Department.TOYS),
            ("books", Department.BOOKS),
        ]
        for username, dept in users:
            existing = db.session.execute(db.select(User).filter_by(username=username)).scalar_one_or_none()
            if existing:
                continue
            user = User(username=username, department=dept)
            user.set_password("password")
            db.session.add(user)
        db.session.commit()
        print("Seeded users with default password 'password'")

    @app.cli.command("seed-admin")
    def seed_admin():
        from .models import User
        existing = db.session.execute(db.select(User).filter_by(username="admin")).scalar_one_or_none()
        if not existing:
            admin = User(username="admin", department=Department.GIFTS, is_admin=True)
            admin.set_password("admin123")
            db.session.add(admin)
            db.session.commit()
            print("Admin user created: admin / admin123")
        else:
            existing.is_admin = True
            db.session.commit()
            print("Admin user already exists; ensured is_admin=True")


