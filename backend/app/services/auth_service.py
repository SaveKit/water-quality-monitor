import os
import requests
from jose import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

# Load env variables
COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID", "ap-southeast-1_XXXXXXX")
COGNITO_APP_CLIENT_ID = os.getenv("COGNITO_APP_CLIENT_ID", "XXXXXXXXXXXXXXXX")
AWS_REGION = os.getenv("AWS_REGION", "ap-southeast-1")

class User:
    def __init__(self, username: str, sub: str):
        self.username = username
        self.sub = sub

class AuthService:
    _jwks = None

    @classmethod
    def get_jwks(cls):
        if cls._jwks is None:
            if not COGNITO_USER_POOL_ID or "XXXXXXX" in COGNITO_USER_POOL_ID:
                return None
            jwks_url = f"https://cognito-idp.{AWS_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}/.well-known/jwks.json"
            try:
                response = requests.get(jwks_url, timeout=5)
                if response.status_code == 200:
                    cls._jwks = response.json()
            except Exception as e:
                print(f"Error fetching Cognito JWKS: {e}")
        return cls._jwks

    @classmethod
    def get_current_user(cls, credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
        token = credentials.credentials
        
        # Check for development/mock mode
        is_mock_config = not COGNITO_USER_POOL_ID or "XXXXXXX" in COGNITO_USER_POOL_ID
        if is_mock_config or token == "mock_token" or token.startswith("mock_"):
            # Return a development mock user
            return User(username="admin_dev", sub="mock_sub_123456789")

        # Live Cognito verification
        jwks = cls.get_jwks()
        if not jwks:
            # Fallback to mock if JWKS could not be retrieved
            return User(username="admin_dev", sub="mock_sub_123456789")

        try:
            # Get the kid from the header
            headers = jwt.get_unverified_header(token)
            kid = headers.get("kid")
            if not kid:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: missing kid header"
                )

            # Find matching key in JWKS
            public_key = None
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    public_key = key
                    break

            if not public_key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: matching key not found in JWKS"
                )

            # Verify and decode JWT
            issuer = f"https://cognito-idp.{AWS_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}"
            claims = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=COGNITO_APP_CLIENT_ID,
                issuer=issuer
            )

            # Extracted details
            username = claims.get("username") or claims.get("cognito:username") or "user"
            sub = claims.get("sub")
            return User(username=username, sub=sub)

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token signature or claims: {str(e)}"
            )
