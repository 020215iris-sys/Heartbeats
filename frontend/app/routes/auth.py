from flask import Blueprint, render_template, redirect, url_for, flash, session
from ..forms.auth import LoginForm, SignupForm
from ..services import api_client
from ..services import guest as guest_svc
from ..services.api_client import SignupError

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
            guest_svc.end_guest_session()

            # 세션에 사용자 정보 저장
            session["access_token"] = result["access_token"]
            session["user_id"] = result["id"]
            session["email"] = form.email.data
            session["nickname"] = result["nickname"]
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
        try:
            result = api_client.signup(
                email=form.email.data,
                password=form.password.data,
                role=form.role.data,
                nickname=form.nickname.data,
                phone_number=form.phone_number.data,
            )
        except SignupError as e:
            # 어떤 필드 문제인지에 따라 해당 필드 바로 아래 에러 표시.
            # form.email.errors는 list라서 append 가능.
            if e.code == "email_taken":
                form.email.errors.append("이미 사용 중인 이메일이에요")
            elif e.code == "phone_taken":
                form.phone_number.errors.append("이미 사용 중인 휴대폰 번호예요")
            # 폼 재렌더링으로 fallthrough
        else:
            # 가입 성공 (try 블록이 예외 없이 끝났을 때만 실행)
            guest_svc.end_guest_session()

            session["access_token"] = result["access_token"]
            session["user_id"] = result["id"]
            session["email"] = result["email"]
            session["nickname"] = result["nickname"]
            session["role"] = result["role"]

            if result.get("needs_guardian_link"):
                flash("가입을 환영해요! 곧 사용자 연결 단계로 안내해드릴게요.", "info")
            else:
                flash("가입을 환영해요! 간단한 설문부터 시작할 예정이에요.", "info")

            return redirect(url_for("main.landing"))

    return render_template("auth/signup.html", form=form)


@bp.route("/logout")
def logout():
    session.clear()
    flash("로그아웃되었어요.", "info")
    return redirect(url_for("main.landing"))
