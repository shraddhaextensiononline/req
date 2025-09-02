SHRADDHA EXTENSION - Customer Tracker App

Simple requirement tracking for Gifts, Stationery, Toys, and Books departments.

Features
- Departmental login (Gifts, Stationery, Toys, Books)
- Create requirements with customer, staff, details, and image upload
- Status workflow (New, In Progress, Fulfilled) with image required for Fulfilled
- Admin dashboard to view all departments
- Filters by staff, customer, status (default Open)

Local Setup
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export FLASK_APP=run.py
flask db upgrade
flask seed        # seed department users (password: password)
flask seed-admin  # seed admin (admin/admin123)
python run.py
```

Environment
- SECRET_KEY: Flask secret (set in prod)
- DATABASE_URL: SQLAlchemy database URI (defaults to sqlite:///app.db)
- UPLOAD_FOLDER: uploads directory (defaults to ./uploads)

Prod Notes
- Use Gunicorn + Nginx. See deployment steps provided in chat.



