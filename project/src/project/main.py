from datetime import timedelta
from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import jwt

from src.project.database import engine, Base, get_db, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS, SECRET_KEY, ALGORITHM
import src.project.models
import src.project.crud as crud
from src.project.schemas import ContactCreate, ContactUpdate, ContactResponse, UserCreate, UserResponse, Token, TokenRefreshRequest
from src.project.auth import verify_password, create_access_token, create_refresh_token, get_current_user

app = FastAPI(title="Contacts API", version="2.0.0")

Base.metadata.create_all(bind=engine)

@app.post("/auth/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(user_data: UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user_data.email)
    if db_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    return crud.create_user(db=db, user_data=user_data)

@app.post("/auth/login", response_model=Token, status_code=status.HTTP_201_CREATED)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, email=form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": user.email}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    refresh_token = create_refresh_token(data={"sub": user.email}, expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    
    crud.update_user_refresh_token(db, user, refresh_token)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@app.post("/auth/refresh", response_model=Token, status_code=status.HTTP_201_CREATED)
def refresh_token(body: TokenRefreshRequest, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(body.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        
    user = crud.get_user_by_email(db, email=email)
    if not user or user.refresh_token != body.refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        
    access_token = create_access_token(data={"sub": user.email}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    new_refresh_token = create_refresh_token(data={"sub": user.email}, expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    
    crud.update_user_refresh_token(db, user, new_refresh_token)
    return {"access_token": access_token, "refresh_token": new_refresh_token, "token_type": "bearer"}

@app.post("/contacts", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
def create_contact(contact: ContactCreate, db: Session = Depends(get_db), current_user: src.project.models.User = Depends(get_current_user)):
    return crud.create_contact(db=db, contact=contact, user_id=current_user.id)

@app.get("/contacts", response_model=list[ContactResponse])
def read_contacts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: src.project.models.User = Depends(get_current_user)):
    return crud.get_contacts(db=db, user_id=current_user.id, skip=skip, limit=limit)

@app.get("/contacts/search", response_model=list[ContactResponse])
def search_contacts(query: str = Query(..., min_length=1), db: Session = Depends(get_db), current_user: src.project.models.User = Depends(get_current_user)):
    return crud.search_contacts(db=db, query=query, user_id=current_user.id)

@app.get("/contacts/birthdays", response_model=list[ContactResponse])
def get_upcoming_birthdays(db: Session = Depends(get_db), current_user: src.project.models.User = Depends(get_current_user)):
    return crud.get_upcoming_birthdays(db=db, user_id=current_user.id)

@app.get("/contacts/{contact_id}", response_model=ContactResponse)
def read_contact(contact_id: int, db: Session = Depends(get_db), current_user: src.project.models.User = Depends(get_current_user)):
    db_contact = crud.get_contact_by_id(db=db, contact_id=contact_id, user_id=current_user.id)
    if db_contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return db_contact

@app.put("/contacts/{contact_id}", response_model=ContactResponse)
def update_contact(contact_id: int, contact_data: ContactUpdate, db: Session = Depends(get_db), current_user: src.project.models.User = Depends(get_current_user)):
    db_contact = crud.update_contact(db=db, contact_id=contact_id, contact_data=contact_data, user_id=current_user.id)
    if db_contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return db_contact

@app.delete("/contacts/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact(contact_id: int, db: Session = Depends(get_db), current_user: src.project.models.User = Depends(get_current_user)):
    db_contact = crud.delete_contact(db=db, contact_id=contact_id, user_id=current_user.id)
    if db_contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return None