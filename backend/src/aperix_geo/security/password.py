"""Password hashing (bcrypt via passlib)."""

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def password_strength_error(password: str) -> str | None:
    """至少 8 位，且字母 / 数字 / 特殊符号至少包含两种。"""
    if len(password) < 8:
        return "密码至少 8 位"
    categories = 0
    if any(c.isalpha() for c in password):
        categories += 1
    if any(c.isdigit() for c in password):
        categories += 1
    if any(not c.isalnum() for c in password):
        categories += 1
    if categories < 2:
        return "密码需包含字母、数字、特殊符号中的至少两种"
    return None
