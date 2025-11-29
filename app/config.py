import os
from dotenv import load_dotenv

if os.getenv("ENV", "development") == "development":
    load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
API_URL = os.getenv("API_URL")
