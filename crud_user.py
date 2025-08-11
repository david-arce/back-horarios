from sqlalchemy.orm import Session
import models, schemas
from security import get_password_hash
from schemas import UserCreate
from models import User

def get_user(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()
 
def create_user(db: Session, user: UserCreate):
    hashed_pw = get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_pw,
        user_type=user.user_type
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user