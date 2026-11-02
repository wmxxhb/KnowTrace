from fastapi import Depends
from sqlalchemy.orm import Session

from ..database.sql_session import get_db
from ..database.models import User


def get_current_user(db: Session = Depends(get_db)):
    # Single-user workspace: reuse existing data without requiring a login.
    user = db.query(User).order_by(User.id).first()
    if user is None:
        user = User(
            username="local",
            email="local@localhost",
            password_hash="",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user
