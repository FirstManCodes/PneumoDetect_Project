# create_db.py
from app import app, db
from database.models import User
from werkzeug.security import generate_password_hash

with app.app_context():
    db.create_all()
    # create admin user (change password)
    if not User.query.filter_by(email='admin@example.com').first():
        admin = User(
            username='admin',
            email='admin@example.com',
            password_hash=generate_password_hash('AdminPass123'),
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        print("Admin user created (admin@example.com / AdminPass123)")
    else:
        print("Admin user already exists")
    print("Database created/updated")
