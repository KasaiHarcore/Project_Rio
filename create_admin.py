"""
Script to create a new Admin user manually.
"""

import sys
import getpass
from pathlib import Path


def _bootstrap_src_layout() -> None:
    repo_root = Path(__file__).resolve().parent
    src_dir = repo_root / "src"
    if src_dir.exists() and str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))


try:
    from infrastructure.database.session import get_db_context
    from models.user import User, UserRole
    from infrastructure.security.auth import get_password_hash
    from utils.log import (
        log_info,
        log_success,
        log_error,
        configure_logging_from_env,
    )
except ModuleNotFoundError:
    _bootstrap_src_layout()
    from infrastructure.database.session import get_db_context
    from models.user import User, UserRole
    from infrastructure.security.auth import get_password_hash
    from utils.log import (
        log_info,
        log_success,
        log_error,
        configure_logging_from_env,
    )

configure_logging_from_env()

def create_admin():
    print("=== Create Admin User ===")
    username = input("Enter admin username: ").strip()
    email = input("Enter admin email: ").strip()
    password = getpass.getpass("Enter admin password: ").strip()
    confirm = getpass.getpass("Confirm password: ").strip()
    
    if password != confirm:
        print("Error: Passwords do not match!")
        return

    if not username or not email or not password:
        print("Error: All fields are required!")
        return

    try:
        with get_db_context() as session:
            existing = session.query(User).filter(
                (User.username == username) | (User.email == email)
            ).first()
            
            if existing:
                print(f"User with username '{username}' or email '{email}' already exists.")
                # Optional: Promote existing user
                promote = input("Do you want to promote this user to ADMIN? (y/n): ").lower()
                if promote == 'y':
                    existing.role = UserRole.ADMIN
                    session.commit()
                    log_success(f"User '{existing.username}' promoted to ADMIN.")
                return

            new_admin = User(
                username=username,
                email=email,
                hashed_password=get_password_hash(password),
                role=UserRole.ADMIN
            )
            session.add(new_admin)
            session.commit()
            log_success(f"Admin user '{username}' created successfully!")
            
    except Exception as e:
        log_error(f"Failed to create admin: {e}")
        print(f"Error: {e}")

if __name__ == "__main__":
    create_admin()
