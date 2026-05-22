"""
채팅 메시지 입력 폼.
"""

from flask_wtf import FlaskForm
from wtforms import TextAreaField
from wtforms.validators import DataRequired, Length


class ChatMessageForm(FlaskForm):
    """사용자가 보내는 한 통의 메시지."""

    message = TextAreaField(
        "메시지",
        validators=[
            DataRequired(message="메시지를 입력해주세요"),
            # 너무 짧은 (공백만) 메시지는 strip 후 다시 검증 (라우트에서),
            # 너무 긴 메시지는 미리 차단해서 백엔드 부담 줄임
            Length(
                min=1, max=2000,
                message="메시지는 1~2000자 사이로 입력해주세요",
            ),
        ],
    )