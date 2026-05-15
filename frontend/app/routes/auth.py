from flask import Blueprint, render_template, redirect, url_for, flash, session
from ..forms.auth import LoginForm, SignupForm
from ..services import api_client

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        result = api_client.login(
            email=form.email.data,
            password=form.password.data,
            role=form.role.data,
        )

        if result:
            # 세션에 사용자 정보 저장
            session["access_token"] = result["access_token"]
            session["email"] = form.email.data
            session["role"] = result["role"]

            flash("환영해요! 로그인되었어요.", "info")
            return redirect(url_for("main.landing"))
        else:
            flash("이메일이나 비밀번호가 올바르지 않아요.", "error")

    return render_template("auth/login.html", form=form)


@bp.route("/signup", methods=["GET", "POST"])
def signup():
    form = SignupForm()

    if form.validate_on_submit():
        result = api_client.signup(
            email=form.email.data,
            password=form.password.data,
            role=form.role.data,
        )

        if result:
            session["access_token"] = result["access_token"]
            session["email"] = form.email.data
            session["role"] = result["role"]

            # 역할별로 다음 단계 안내
            if result.get("needs_guardian_link"):
                flash("가입을 환영해요! 곧 사용자 연결 단계로 안내해드릴게요.", "info")
            else:
                flash("가입을 환영해요! 간단한 설문부터 시작할 예정이에요.", "info")

            return redirect(url_for("main.landing"))
        else:
            flash("이미 사용 중인 이메일이에요.", "error")

    return render_template("auth/signup.html", form=form)


@bp.route("/logout")
def logout():
    session.clear()
    flash("로그아웃되었어요.", "info")
    return redirect(url_for("main.landing"))