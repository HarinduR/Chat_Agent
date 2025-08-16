# CQ_Manager_Agent/config.py
import os

class Config:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DATA_DIR = os.path.join(BASE_DIR, "data")

    KNOWLEDGE_BASE_PATH = os.path.join(DATA_DIR, "knowledge_base")
    VECTOR_STORE_PATH = os.path.join(DATA_DIR, "vector_store")
    MODEL_PATH = os.path.join(DATA_DIR, "models")

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "sqlite:///" + os.path.join(DATA_DIR, "database.db")
    )

    SECRET_KEY = os.getenv("SECRET_KEY", "development-key-change-in-production")
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 30
