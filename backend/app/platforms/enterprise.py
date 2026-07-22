"""Enterprise Platform - Auth & RBAC (P8)."""

from datetime import datetime, timedelta
from typing import Any

from jose import jwt
from passlib.context import CryptContext

from app.config import settings
from app.models.schemas import User, UserRole
from app.seed.loader import seed_data

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ROLE_PERMISSIONS = {
    UserRole.SAFETY_OFFICER: {"acknowledge", "escalate", "dismiss", "emergency", "view_evidence", "view_dashboard"},
    UserRole.PERMIT_OFFICER: {"view_permits", "override_permit", "view_dashboard"},
    UserRole.SUPERVISOR: {"zone_evacuate", "acknowledge", "view_dashboard"},
    UserRole.COMPLIANCE_OFFICER: {"view_evidence", "export_audit", "view_reports"},
    UserRole.EXECUTIVE: {"view_executive", "export_reports"},
    UserRole.WORKER: {"view_mobile", "acknowledge_alert"},
    UserRole.ADMIN: {"*"},
}


def create_token(user: User) -> str:
    expire = datetime.utcnow() + timedelta(hours=12)
    payload = {"sub": user.username, "role": user.role.value, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def authenticate(username: str, password: str) -> User | None:
    user_data = seed_data.users.get(username)
    if not user_data or user_data["password"] != password:
        return None
    return User(
        user_id=user_data["user_id"],
        username=username,
        role=user_data["role"],
        name=user_data["name"],
        zone_id=user_data.get("zone_id"),
    )


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except Exception:
        return None


def check_permission(role: UserRole | str, action: str) -> bool:
    if isinstance(role, str):
        try:
            role = UserRole(role)
        except ValueError:
            return False
    perms = ROLE_PERMISSIONS.get(role, set())
    return "*" in perms or action in perms
