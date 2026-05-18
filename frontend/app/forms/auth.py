from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, RadioField
from wtforms.validators import DataRequired, Email, Length, EqualTo, AnyOf

# 역할 선택지 (사용자, 보호자)
ROLE_CHOICES = [
    ("user", "사용자"),
    ("guardian", "보호자"),
]


class LoginForm(FlaskForm):
    role = RadioField(
        '역할',
        choices=ROLE_CHOICES,
        default='user',
        validate_choice=[
            DataRequired(message='역할을 선택해주세요')
        ]
    )
    email = StringField(
        "이메일",
        validators=[
            DataRequired(message="이메일을 입력해주세요"),
            Email(message="이메일 형식이 올바르지 않아요"),
        ],
    )
    password = PasswordField(
        "비밀번호",
        validators=[DataRequired(message="비밀번호를 입력해주세요")],
    )
    remember = BooleanField("로그인 상태 유지")


class SignupForm(FlaskForm):
    role = RadioField(
        "역할",
        choices=ROLE_CHOICES,
        default="user",
        validators=[
            DataRequired(message="역할을 선택해주세요"),
            AnyOf(["user", "guardian"], message="잘못된 역할이에요"),
        ],
    )
    email = StringField(
        "이메일",
        validators=[
            DataRequired(message="이메일을 입력해주세요"),
            Email(message="이메일 형식이 올바르지 않아요"),
        ],
    )
    password = PasswordField(
        "비밀번호",
        validators=[
            DataRequired(message="비밀번호를 입력해주세요"),
            Length(min=8, message="비밀번호는 8자 이상이어야 해요"),
        ],
    )
    password_confirm = PasswordField(
        "비밀번호 확인",
        validators=[
            DataRequired(message="비밀번호 확인을 입력해주세요"),
            EqualTo("password", message="비밀번호가 일치하지 않아요"),
        ],
    )