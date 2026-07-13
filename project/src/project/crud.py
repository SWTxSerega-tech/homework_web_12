from datetime import date, timedelta
from sqlalchemy import or_, and_, extract
from sqlalchemy.orm import Session
from src.project.models import Contact, User
from src.project.schemas import ContactCreate, ContactUpdate, UserCreate
from src.project.auth import get_password_hash

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, user_data: UserCreate):
    hashed_pwd = get_password_hash(user_data.password)
    db_user = User(email=user_data.email, hashed_password=hashed_pwd)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user_refresh_token(db: Session, user: User, token: str | None):
    user.refresh_token = token
    db.commit()

def get_contacts(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(Contact).filter(Contact.user_id == user_id).offset(skip).limit(limit).all()

def get_contact_by_id(db: Session, contact_id: int, user_id: int):
    return db.query(Contact).filter(Contact.id == contact_id, Contact.user_id == user_id).first()

def search_contacts(db: Session, query: str, user_id: int):
    return db.query(Contact).filter(
        Contact.user_id == user_id,
        or_(
            Contact.first_name.ilike(f"%{query}%"),
            Contact.last_name.ilike(f"%{query}%"),
            Contact.email.ilike(f"%{query}%")
        )
    ).all()

def get_upcoming_birthdays(db: Session, user_id: int):
    today = date.today()
    days_range = [today + timedelta(days=i) for i in range(8)]
    
    conditions = []
    for d in days_range:
        conditions.append(
            and_(
                extract('month', Contact.birthday) == d.month,
                extract('day', Contact.birthday) == d.day
            )
        )
        
    return db.query(Contact).filter(Contact.user_id == user_id, or_(*conditions)).all()

def create_contact(db: Session, contact: ContactCreate, user_id: int):
    db_contact = Contact(**contact.model_dump(), user_id=user_id)
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact)
    return db_contact

def update_contact(db: Session, contact_id: int, contact_data: ContactUpdate, user_id: int):
    db_contact = get_contact_by_id(db, contact_id, user_id)
    if not db_contact:
        return None
    
    for key, value in contact_data.model_dump().items():
        setattr(db_contact, key, value)
        
    db.commit()
    db.refresh(db_contact)
    return db_contact

def delete_contact(db: Session, contact_id: int, user_id: int):
    db_contact = get_contact_by_id(db, contact_id, user_id)
    if db_contact:
        db.delete(db_contact)
        db.commit()
    return db_contact