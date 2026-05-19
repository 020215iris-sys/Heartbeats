from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, RadioField
from wtforms.validators import (
    DataRequired,
    Email,
    Length,
    EqualTo,
    AnyOf,
    Optional,
    Regexp,
)

# 역할 선택지 (사용자, 보호자)
ROLE_CHOICES = [
    ("user", "사용자"),
    ("guardian", "보호자"),
]


# ====== 로그인부분 ======
class LoginForm(FlaskForm):
    # ====== 아이디 (USERS.id) ======
    role = RadioField(
        "역할",
        choices=ROLE_CHOICES,
        default="user",
        validate_choice=[
            DataRequired(message="역할을 선택해주세요"),
            AnyOf(["user", "guardian"], message="잘못된 역할이에요"),],
    )
    # ====== 이메일 (USERS.email) ======
    email = StringField(
        "이메일",
        validators=[
            DataRequired(message="이메일을 입력해주세요"),
            Email(message="이메일 형식이 올바르지 않아요"),
        ],
    )
    # ====== 비밀번호 (USERS.hashed_password) ======
    password = PasswordField(
        "비밀번호",
        validators=[DataRequired(message="비밀번호를 입력해주세요")],
    )
    remember = BooleanField("로그인 상태 유지")


# ====== 회원가입 부분 ======
class SignupForm(FlaskForm):
    # ====== 아이디 (USERS.role) ======
    role = RadioField(
        "역할",
        choices=ROLE_CHOICES,
        default="user",
        validators=[
            DataRequired(message="역할을 선택해주세요"),
            AnyOf(["user", "guardian"], message="잘못된 역할이에요"),
        ],
    )
    # ====== 아이디 (USERS.email) ======
    email = StringField(
        "이메일",
        validators=[
            DataRequired(message="이메일을 입력해주세요"),
            Email(message="이메일 형식이 올바르지 않아요"),
        ],
    )
    # ====== 닉네임 (USERS.nickname) ======
    nickname = StringField(
        "닉네임",
        validators=[
            DataRequired(message="닉네임을 입력해주세요"),
            Length(min=2, max=20, message="닉네임은 2~20자로 입력해주세요"),
        ],
    )
    # ====== 휴대폰 번호 (USERS.phone_number) ======
    phone_number = StringField(
        "휴대폰 번호",
        validators=[
            # Optional(),  # 휴대폰 번호 옵션으로 넣을 경우
            DataRequired(message="휴대폰 번호를 입력해주세요"),
            Regexp(
                r"^01[0-9]-?\d{3,4}-?\d{4}$",
                message="010-1234-5678 형식으로 입력해주세요",
            ),
        ],
    )
    # ====== 비밀번호 해싱후(USERS.hashed_password) ======
    password = PasswordField(
        "비밀번호",
        validators=[
            DataRequired(message="비밀번호를 입력해주세요"),
            Length(min=8, message="비밀번호는 8자 이상이어야 해요"),
        ],
    )
    # ====== 비밀번호 확인부 ======
    password_confirm = PasswordField(
        "비밀번호 확인",
        validators=[
            DataRequired(message="비밀번호 확인을 입력해주세요"),
            EqualTo("password", message="비밀번호가 일치하지 않아요"),
        ],
    )
