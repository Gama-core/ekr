# app/services/crud/crud_user.py

from sqlalchemy.orm import Session
from typing import Optional, List
from app import models, schemas
from app.core.security import get_password_hash # We'll need to create this utility

def get_user(db: Session, user_id: int) -> Optional[models.AppUser]:
    """
    Retrieve a user by their ID.
    """
    return db.query(models.AppUser).filter(models.AppUser.id == user_id).first()

def get_user_by_username(db: Session, username: str) -> Optional[models.AppUser]:
    """
    Retrieve a user by their username.
    """
    return db.query(models.AppUser).filter(models.AppUser.username == username).first()

def get_user_by_email(db: Session, email: str) -> Optional[models.AppUser]:
    """
    Retrieve a user by their email.
    (Ensure your AppUser model has an index on email if this is frequently used)
    """
    return db.query(models.AppUser).filter(models.AppUser.email == email).first()

def get_all_users(db: Session, skip: int = 0, limit: int = 100) -> List[models.AppUser]:
    """
    Retrieve all users with pagination.
    """
    return db.query(models.AppUser).offset(skip).limit(limit).all()

def create_user(db: Session, user_in: schemas.AppUserCreate) -> models.AppUser:
    """
    Create a new user.
    Passwords should be hashed before storing.
    """
    # Check if username or email already exists (if they are unique constraints)
    if get_user_by_username(db, username=user_in.username):
        raise ValueError(f"Username '{user_in.username}' already registered.")
    if user_in.email and get_user_by_email(db, email=user_in.email):
        # Note: Your DDL for AppUser model for 'email' did not have unique=True.
        # If it should be unique, add it to the model and handle this error.
        # If not unique, this check might be less critical or handled differently.
        print(f"Warning: Email '{user_in.email}' is being registered, ensure uniqueness if required.")
        # raise ValueError(f"Email '{user_in.email}' already registered.")


    hashed_password = get_password_hash(user_in.password)
    db_user = models.AppUser(
        username=user_in.username,
        hashed_password=hashed_password, # Store the hashed password
        email=user_in.email,
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        phone=user_in.phone,
        title=user_in.title,
        date_of_birth=user_in.date_of_birth,
        enabled=user_in.enabled, # From schema, which defaults to True (maps to 1 if DB is int)
        version=0 # Initial version
    )
    # Important: Your AppUser model has 'password' field, not 'hashed_password'.
    # Adjust the model or this CRUD:
    # Option 1: Rename 'password' to 'hashed_password' in AppUser model
    # Option 2: Set db_user.password = hashed_password here.
    # Let's assume you'll use db_user.password for storing the hash.
    db_user.password = hashed_password # Storing hashed password in the 'password' field

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(
    db: Session,
    user_id: int,
    user_update: schemas.AppUserUpdate  # Assuming you create an AppUserUpdate schema
) -> Optional[models.AppUser]:
    """
    Update an existing user.
    (Requires an AppUserUpdate Pydantic schema)
    """
    db_user = get_user(db, user_id)
    if not db_user:
        return None

    update_data = user_update.model_dump(exclude_unset=True)

    if "username" in update_data and update_data["username"] != db_user.username:
        existing_user = get_user_by_username(db, username=update_data["username"])
        if existing_user and existing_user.id != user_id:
            raise ValueError(f"Username '{update_data['username']}' already taken.")

    if "email" in update_data and update_data["email"] != db_user.email and update_data["email"] is not None:
        # Again, consider if email should be unique.
        existing_user_by_email = get_user_by_email(db, email=update_data["email"])
        if existing_user_by_email and existing_user_by_email.id != user_id:
            # raise ValueError(f"Email '{update_data['email']}' already taken.")
            print(f"Warning: Updating to email '{update_data['email']}' which might already be in use by another user.")


    for key, value in update_data.items():
        if key == "password": # Special handling for password updates
            if value: # Only update if a new password is provided
                db_user.password = get_password_hash(value) # Hash the new password
        else:
            setattr(db_user, key, value)

    db_user.version = (db_user.version or 0) + 1
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user_password(db: Session, user_id: int, new_password: str) -> Optional[models.AppUser]:
    """
    Specifically update a user's password.
    """
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    db_user.password = get_password_hash(new_password)
    db_user.version = (db_user.version or 0) + 1
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user(db: Session, user_id: int) -> Optional[models.AppUser]:
    """
    Delete a user.
    (Consider implications: owned documents, notes, communications. How to handle them?)
    """
    db_user = get_user(db, user_id)
    if not db_user:
        return None

    # Handle orphaned records (documents, notes, communications owned by this user)
    # Option 1: Database CASCADE DELETE constraints.
    # Option 2: Set FKs to NULL if allowed (e.g., document.owned_by_id = NULL).
    # Option 3: Reassign to a system user.
    # Option 4: Prevent deletion if user owns critical data.
    # This logic can be complex and depends on your application's business rules.
    # For now, we'll just delete the user.
    # Example: If you want to nullify ownership (assuming owned_by_id allows NULL)
    # db.query(models.Document).filter(models.Document.owned_by_id == user_id).update({"owned_by_id": None})
    # db.query(models.Note).filter(models.Note.owner_id == user_id).update({"owner_id": None}) # If allowed

    db.delete(db_user)
    db.commit()
    return db_user

# Authentication helper (can be expanded)
# from app.core.security import verify_password # We'll need this too
# def authenticate_user(db: Session, username: str, password_to_check: str) -> Optional[models.AppUser]:
#     user = get_user_by_username(db, username=username)
#     if not user:
#         return None
#     if not verify_password(password_to_check, user.password): # Assuming user.password stores the hash
#         return None
#     return user