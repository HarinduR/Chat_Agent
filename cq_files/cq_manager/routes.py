# cq_manager/routes.py
from flask import render_template, request, jsonify, session, redirect, url_for
import uuid

from cq_files.cq_manager import chatbot_bp
from cq_files.cq_manager.chat.processor import ChatProcessor
from cq_files.cq_manager.chat.suggestions_generator import SuggestionsGenerator

chat_processor = ChatProcessor()
suggestions_generator = SuggestionsGenerator()


@chatbot_bp.route("/")
def index():
    return redirect(url_for("chatbot.chatbot_dashboard"))

@chatbot_bp.route("/chatbot-dashboard")
def chatbot_dashboard():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    return render_template("chat.html")


@chatbot_bp.route("/chat", methods=["POST"])
def process_chat():
    data = request.get_json(silent=True) or {}
    user_message = data.get("message")
    action = data.get("action")
    session_id = session.get("session_id", str(uuid.uuid4()))

    if not user_message and not action:
        return jsonify({"error": "No message or action provided"}), 400

    try:
        if action:
            if action == "schedule":
                bot_text = chat_processor.process_message("Show me my waste collection schedule", session_id)
            elif action == "recycle-guide":
                bot_text = chat_processor.process_message("What's the guide for recycling different materials?", session_id)
            elif action == "report-issue":
                bot_text = chat_processor.process_message("I want to report an issue with waste collection", session_id)
            elif action == "tips":
                bot_text = chat_processor.process_message("Share some eco-friendly waste management tips", session_id)
            else:
                bot_text = "I didn't recognize that quick action. Try asking a question."
        else:
            bot_text = chat_processor.process_message(user_message, session_id)

        suggs = suggestions_generator.generate_suggestions(user_message or action, bot_text)
        return jsonify({"response": bot_text, "suggestions": suggs})
    except Exception as e:
        print(f"/chat error: {e}")
        return jsonify({"error": "An error occurred processing your request"}), 500
