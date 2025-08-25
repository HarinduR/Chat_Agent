# app.py (project root)
import os
from flask import Flask
from dotenv import load_dotenv

# Load .env early
load_dotenv()

from cq_files.cq_manager import chatbot_bp  # noqa: E402

def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv("SECRET_KEY", "change-this-in-production")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///data/database.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    app.register_blueprint(chatbot_bp, url_prefix="/")  # exposes /chatbot-dashboard and /chat
    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)