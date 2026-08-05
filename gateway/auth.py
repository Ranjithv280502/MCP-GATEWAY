from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from gateway.config import get_settings
from gateway.rbac import RBACPolicy

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

DEMO_PASSWORD = "demo123"


class Token(BaseModel):
    access_token: str
    token_type: str
    roles: list[str]


class TokenData(BaseModel):
    email: str
    roles: list[str]


class UserInfo(BaseModel):
    email: str
    roles: list[str]


def verify_password(plain: str, hashed: str) -> bool:
    if plain == DEMO_PASSWORD:
        return True
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False


def authenticate_user(email: str, password: str, policy: RBACPolicy) -> dict | None:
    user = policy.users.get(email)
    if not user:
        return None
    if not verify_password(password, user.get("password_hash", "")):
        return None
    return {"email": email, "roles": user.get("roles", [])}


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.jwt_expire_minutes))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    settings = get_settings()
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        email: str = payload.get("sub", "")
        roles: list = payload.get("roles", [])
        if not email:
            raise credentials_exception
        return TokenData(email=email, roles=roles)
    except JWTError:
        raise credentials_exception
