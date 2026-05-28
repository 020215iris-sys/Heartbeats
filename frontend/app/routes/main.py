from flask import Blueprint, render_template, redirect, url_for
from ..services import guest as guest_svc

bp = Blueprint('main', __name__)


@bp.route('/')
def landing():
    return render_template('landing.html')


@bp.route("/guest/start")
def start_guest():
    guest_svc.start_guest_session()
    return redirect(url_for("chat.room"))