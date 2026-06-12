from datetime import date
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, RadioField, DateField
from wtforms.validators import (
    DataRequired,
    Email,
    Length,
    EqualTo,
    AnyOf,
    Optional,
    Regexp,
    ValidationError
)

# 역할 선택지 (사용자, 보호자)
ROLE_CHOICES = [
    ("user", "사용자"),
    ("guardian", "보호자"),
]

def validate_birth_date(form, field):
    if field.data and field.data > date.today():
        raise ValidationError("미래 날짜는 입력할 수 없습니다.")
    
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
    # ====== 보호자 초대 코드 (보호자 가입 시 필수) ======
    invite_code = StringField(
        "초대 코드",
        validators=[
            Optional(),
            Regexp(r"^\d{8}$", message="초대코드는 숫자 8자리예요"),
        ],
        description="보호자로 가입하는 경우, 피보호자에게 받은 8자리 코드를 입력하세요.",
    )

    def validate_invite_code(self, field):
        # 보호자인데 코드가 비어 있으면 막음 (게이트키퍼)
        if self.role.data == "guardian" and not field.data:
            raise ValidationError("보호자 가입은 초대 코드가 필요해요")
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
    # ====== 생년월일 (USERS.birth_date) ======
    birth_date = DateField(
        "생년월일",
        format="%Y-%m-%d",
        validators=[Optional(), validate_birth_date],
        description="선택 입력입니다.",
        render_kw={
            "autocomplete": "bday",
            "min": "1900-01-01",
            "max": date.today().isoformat(),
        },
    )
    # ====== 성별 (USERS.gender) ======
    gender = RadioField(
        "성별",
        choices=[("male", "남"), ("female", "여"), ("unspecified", "무응답")],
        validators=[
            DataRequired(message="성별을 선택해주세요"),
            AnyOf(["male", "female", "unspecified"], message="잘못된 성별이에요"),
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
