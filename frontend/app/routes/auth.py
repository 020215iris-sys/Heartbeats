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
            session["refresh_token"] = result.get("refresh_token")
            session["user_id"] = result["id"]
            session["email"] = form.email.data
            session["nickname"] = result["nickname"]
            session["role"] = result["role"]

            flash("환영해요! 로그인되었어요.", "info")
            return  redirect(url_for("main.landing"))
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
                gender=form.gender.data,
                birth_date=form.birth_date.data.isoformat() if form.birth_date.data else None,
                invite_code=form.invite_code.data or None
            )
        except SignupError as e:
            # 어떤 필드 문제인지에 따라 해당 필드 바로 아래 에러 표시.
            # form.email.errors는 list라서 append 가능.
            if e.code == "email_taken":
                form.email.errors.append("이미 사용 중인 이메일이에요")
            elif e.code == "phone_taken":
                form.phone_number.errors.append("이미 사용 중인 휴대폰 번호예요")
            elif e.code == "invalid_birth_date":
                form.birth_date.errors.append("생년월일 형식이 올바르지 않아요")
            elif e.code == "invite_code_required":
                form.invite_code.errors.append("보호자 가입은 초대 코드가 필요해요")
            elif e.code == "invalid_or_expired_code":
                form.invite_code.errors.append("초대 코드가 올바르지 않거나 만료됐어요")
            else:
                flash("서버 연결에 실패했어요. 잠시 후 다시 시도해주세요.", "error")
            # 폼 재렌더링으로 fallthrough
        else:
            # 가입 성공 (try 블록이 예외 없이 끝났을 때만 실행)
            guest_svc.end_guest_session()

            session["access_token"] = result["access_token"]
            session["refresh_token"] = result.get("refresh_token")
            session["user_id"] = result["id"]
            session["email"] = result["email"]
            session["nickname"] = result["nickname"]
            session["role"] = result["role"]

            if result.get("needs_guardian_link"):
                flash("가입을 환영해요! 곧 사용자 연결 단계로 안내해드릴게요.", "info")
                return redirect(url_for("main.landing"))
            else:
                flash("가입을 환영해요! 설문을 통해 맞춤 상담을 시작할 수 있어요.", "info")
                return redirect(url_for("main.landing"))

    return render_template("auth/signup.html", form=form)


@bp.route("/logout")
def logout():
    # 백엔드에 요약 저장 + refresh_token 만료 요청
    refresh_token = session.get("refresh_token")
    access_token = session.get("access_token")
    if refresh_token and access_token:
        api_client.logout(refresh_token, access_token)

    session.clear()
    flash("로그아웃되었어요.", "info")
    return redirect(url_for("main.landing"))