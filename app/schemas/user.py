# app/schemas/user.py

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

# --- DEFINE AppUserBase FIRST ---
class AppUserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    title: Optional[str] = Field(None, max_length=50)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    date_of_birth: Optional[datetime] = None
    enabled: bool = True # Use bool for schemas

# --- THEN define classes that inherit from AppUserBase ---
class AppUserCreate(AppUserBase): # Now AppUserBase is known
    password: str = Field(..., min_length=8)

class AppUserResponse(AppUserBase): # Now AppUserBase is known
    id: int
    version: int # Assuming version is part of your user model and you want to expose it

    class Config:
        from_attributes = True # Pydantic V2 (use orm_mode = True for V1)

class UserUpdatePassword(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)

# You might have an AppUserUpdate schema as well
class AppUserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    title: Optional[str] = Field(None, max_length=50)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    date_of_birth: Optional[datetime] = None
    enabled: Optional[bool] = None
