# CQ_Manager_Agent/__init__.py
from flask import Blueprint

chatbot_bp = Blueprint(
    "chatbot", __name__, template_folder="templates", static_folder="static"
)

# import routes to attach endpoints to blueprint
from . import routes  # noqa: E402,F401
