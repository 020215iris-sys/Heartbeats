from flask import Blueprint, render_template, redirect, url_for, abort, jsonify 
from ..services import guest as guest_svc
from ..services.chat_history import get_recent_chats, get_chat, get_chat_messages

bp = Blueprint('main', __name__)


@bp.route('/')
def landing():
    return render_template('landing.html')


@bp.route("/guest/start")
def start_guest():
    guest_svc.start_guest_session()
    return redirect(url_for("chat.room"))

@bp.route("/terms")
def terms():
    return render_template("legal/terms.html")

@bp.route("/privacy")
def privacy():
    return render_template("legal/privacy.html")

@bp.route("/history")
def history():
    chats = get_recent_chats()
    return render_template("chat/history.html", chats=chats)


@bp.route("/history/<chat_id>")
def history_detail(chat_id):
    chat = get_chat(chat_id)
    if chat is None:
        abort(404)
    messages = get_chat_messages(chat_id)
    return render_template("chat/history_detail.html", chat=chat, messages=messages)

@bp.route("/history/<chat_id>/messages")
def history_messages(chat_id):
    if get_chat(chat_id) is None:
        abort(404)
    return jsonify({"chat": get_chat(chat_id), "messages": get_chat_messages(chat_id)})