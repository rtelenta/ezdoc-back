import os
from dotenv import load_dotenv

if os.getenv("ENV", "development") == "development":
    load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
API_URL = os.getenv("API_URL")
SECRET_KEY = os.getenv("SECRET_KEY")

COGNITO_REGION = os.getenv("COGNITO_REGION")
COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID")
COGNITO_APP_CLIENT_ID = os.getenv("COGNITO_APP_CLIENT_ID")
