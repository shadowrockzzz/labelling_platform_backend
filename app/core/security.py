from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
serializer = URLSafeTimedSerializer(settings.SECRET_KEY)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_token(email: str) -> str:
    return serializer.dumps(email)

def verify_token(token: str, max_age: int = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60) -> str | None:
    try:
        return serializer.loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
    
class TokenProvider:
    def create_token(self, email: str) -> str:
        return create_token(email)
    def verify_token(self, token: str):
        return verify_token(token)

token_provider = TokenProvider()

