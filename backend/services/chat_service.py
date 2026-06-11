import os
import re
import random
import uuid
import json
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import Conversation, CounselingSession, Summary
from core.security import verify_access_token
from core.crypto import encrypt_content
from routers.counseling import close_session_with_summary
from services.audit_service import log_sensitive
from services.crisis_response import get_crisis_response_message,save_crisis_event
from services.crisis_tool_schema import CRISIS_TOOL,CRISIS_TOOL_INSTRUCTION

load_dotenv()

# ─────────────────────────────────────────
# Cerebras 클라이언트 (대화모델, OpenAI 호환)
# ─────────────────────────────────────────
groq_client = OpenAI(
    api_key=os.getenv("CEREBRAS_API_KEY"),
    base_url="https://api.cerebras.ai/v1",
)

# ─────────────────────────────────────────
# 프롬프트 로드
# ─────────────────────────────────────────
AGENT_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "../../ai/prompts/active/prompt_agent_prompt.txt")
with open(AGENT_PROMPT_PATH, "r", encoding="utf-8") as f:
    AGENT_PROMPT = f.read()

GENERAL_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "../../ai/prompts/active/general_prompt.txt")
with open(GENERAL_PROMPT_PATH, "r", encoding="utf-8") as f:
    GENERAL_PROMPT = f.read()

# ─────────────────────────────────────────
# 세션별 system_prompt 캐시
# ─────────────────────────────────────────
SESSION_PROMPT_CACHE: dict[str, str] = {}


# ─────────────────────────────────────────
# 외국어 감지 시 대체 응답 (랜덤)
# ─────────────────────────────────────────
FOREIGN_FALLBACK_REPLIES = [
    "괜찮으시면 조금 다른 방향으로 이야기해볼까요?",
    "그렇군요. 좀 더 자세히 얘기해주실 수 있으신가요?",
    "그러셨군요... 잠시 그 마음에 좀 더 머물러봐도 괜찮을까요?",
    "죄송해요. 그 부분에 대한 건 답변이 어려워요.",
]


# ─────────────────────────────────────────
# 외국어 감지
# ─────────────────────────────────────────
def contains_foreign(text: str) -> bool:
    # 한글·숫자·공백·기본 구두점만 허용, 나머지는 외국어로 감지
    # (영어, 한자, 일본어, 전각문자 등 모두 차단)
    pattern = r'[^가-힣ᄀ-ᇿ㄰-㆏0-9\s.,!?~\-\'"()…·%:/*]'
    return bool(re.search(pattern, text))


# ─────────────────────────────────────────
# /chat 비즈니스 로직
# ─────────────────────────────────────────
async def process_chat(
    message: str,
    session_id: str,
    history: list[dict],
    token: str,
    db_sensitive: AsyncSession,
    db_audit: AsyncSession,
) -> str:

    # 1. JWT 토큰에서 user_id 꺼내기
    token = token.replace("Bearer ", "")
    current_user = verify_access_token(token)

    # 2. session_id로 counseling_session 조회 → 없으면 자동 생성
    result = await db_sensitive.execute(
        select(CounselingSession).where(
            CounselingSession.id == uuid.UUID(session_id),
            CounselingSession.deleted_at == None
        )
    )
    counseling_session = result.scalar()

    if not counseling_session:
        counseling_session = CounselingSession(
            id=uuid.UUID(session_id),
            user_id=uuid.UUID(current_user["user_id"]),
            persona_type="empathy",
            is_active=True
        )
        db_sensitive.add(counseling_session)
        await db_sensitive.flush()

    # 3. 60분 타임아웃 체크
    use_summary = False

    last_msg = await db_sensitive.execute(
        select(Conversation)
        .where(Conversation.session_id == uuid.UUID(session_id))
        .order_by(Conversation.created_at.desc())
        .limit(1)
    )
    last = last_msg.scalar()
    if last:
        elapsed = datetime.now(timezone.utc) - last.created_at.replace(tzinfo=timezone.utc)
        if elapsed > timedelta(minutes=60):
            await close_session_with_summary(counseling_session, db_sensitive, db_audit)
            SESSION_PROMPT_CACHE.pop(str(counseling_session.id), None)
            counseling_session.ended_at = datetime.now(timezone.utc)
            counseling_session.is_active = False
            await db_sensitive.flush()
            counseling_session = CounselingSession(
                user_id=uuid.UUID(current_user["user_id"]),
                persona_type="empathy",
                is_active=True
            )
            db_sensitive.add(counseling_session)
            await db_sensitive.flush()
            use_summary = True

    # 4. system_prompt 결정
    summary_result = await db_sensitive.execute(
        select(Summary)
        .where(Summary.user_id == uuid.UUID(current_user["user_id"]))
        .order_by(Summary.created_at.desc())
        .limit(1)
    )
    recent_summary = summary_result.scalar()

    cache_key = str(counseling_session.id)

    if cache_key in SESSION_PROMPT_CACHE:
        system_content = SESSION_PROMPT_CACHE[cache_key]
        print("=== PROMPT: 캐시 사용 ===")

    elif recent_summary:
        # 재상담: Agent가 요약 기반으로 system_prompt 생성
        prompt_agent_input = {
            "nickname": current_user.get("nickname", "사용자"),
            "classification_results": {},
            "summary": {
                "main_complaint": recent_summary.main_complaint,
                "core_topics": recent_summary.core_topics,
                "next_session_notes": recent_summary.next_session_notes,
                "prompt_adjustment": recent_summary.prompt_adjustment,
                "important_memory": recent_summary.important_memory,  
            },
            "risk_level": recent_summary.risk_level,
            "suicidal_mentioned": recent_summary.suicidal_mentioned,
        }

        print("===== AGENT INPUT =====")
        print(json.dumps(prompt_agent_input, ensure_ascii=False, indent=2))
        agent_response = groq_client.chat.completions.create(
            model="llama-3.3-70b",
            messages=[
                {"role": "system", "content": AGENT_PROMPT},
                {"role": "user", "content": json.dumps(prompt_agent_input, ensure_ascii=False)},
            ]
        )
        print("=== PROMPT: 재상담 - Agent 생성 ===")
        raw = agent_response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.strip("`").strip()
            if raw[:4].lower() == "json":
                raw = raw[4:].strip()
        agent_result = json.loads(raw)

        # 추가
        print("=== AGENT PARSED ===")
        print(agent_result)

        # 추가
        print("=== AGENT SYSTEM PROMPT ===")
        print(agent_result["system_prompt"])

        if contains_foreign(agent_result["system_prompt"]):
            print("=== AGENT FOREIGN DETECTED ===")
            print(agent_result["system_prompt"])

            agent_result["system_prompt"] = (
                f"사용자 닉네임은 '{current_user.get('nickname', '사용자')}'이다. "
                "현재 상태를 탐색하고 이전 회차 기억과 감정 반영을 우선한다. "
                "질문은 한 번에 하나씩 제시한다. "
                "정서적 안정화를 우선한다."
            )

        print(
           "foreign =",
            contains_foreign(agent_result["system_prompt"])
        )

        system_content = GENERAL_PROMPT + "\n\n" + agent_result["system_prompt"]
        system_content += "\n\n" + CRISIS_TOOL_INSTRUCTION
        SESSION_PROMPT_CACHE[cache_key] = system_content
        print("=== system_prompt ===") # Agent가 생성한 system_prompt 내용
        print(agent_result["system_prompt"])

    else:
        # 첫 대화: general_prompt 사용
        system_content = GENERAL_PROMPT
        system_content += "\n\n" + CRISIS_TOOL_INSTRUCTION
        SESSION_PROMPT_CACHE[cache_key] = system_content
        print("=== PROMPT: 첫 상담 - GENERAL_PROMPT 사용 ===")


    # 5. Groq 응답 요청
    print("=== PROMPT 사용 ===")
    print(f"=== {system_content} ===") #최종 사용된 전체 프롬프트
    print("===================")
    messages_to_send = (
        [{"role": "system", "content": system_content},
         {"role": "user", "content": message}]
        if use_summary else
        [{"role": "system", "content": system_content},
         *history,
         {"role": "user", "content": message}]
    )

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b",
        messages=messages_to_send,
        tools=[CRISIS_TOOL],
        tool_choice="auto"
    )
    message_obj = response.choices[0].message
    is_crisis = False

    print("===== TOOL CALLS =====")
    print(message_obj.tool_calls)
    print("======================")


    if message_obj.tool_calls:
        
        is_crisis = True

        args = json.loads(
            message_obj.tool_calls[0].function.arguments
        )

        severity = args["severity"]
        category = args["category"]
        reason = args["reason"]

        print("severity =", severity)
        print("category =", category)
        print("reason =", reason)

        print(
            f"=== CRISIS TOOL === "
            f"{severity} / {category} / {reason}"
        )

        reply = get_crisis_response_message(severity)
        
    else:
        reply = response.choices[0].message.content


    print("=== REPLY CHECK ===", reply) #외국어 감지 필터 들어가기 전
    

    # 6. 외국어 감지 시 재요청
    if not is_crisis and contains_foreign(reply):
        reinforced = system_content + "\n\n모든 응답은 반드시 한글로만 작성한다. 영어를 포함한 외국어 사용 금지."
        SESSION_PROMPT_CACHE[cache_key] = reinforced  # 강화된 언어 규칙 캐시 저장
        messages_foreign = (
            [{"role": "system", "content": reinforced},
             {"role": "user", "content": message}]
            if use_summary else
            [{"role": "system", "content": reinforced},
             *history,
             {"role": "user", "content": message}]
        )
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b",
            messages=messages_foreign
        )
        reply = response.choices[0].message.content
        print("=== REPLY CHECK (재요청 후) ===", reply)
        if contains_foreign(reply):
            reply = random.choice(FOREIGN_FALLBACK_REPLIES)

    print("=== REPLY CHECK (필터 후) ===", reply)

    # 7. 사용자/AI 메시지 저장
    ciphertext, key_id = encrypt_content(message)
    user_msg = Conversation(
        session_id=counseling_session.id,
        user_id=uuid.UUID(current_user["user_id"]),
        role="user",
        message_type="text",
        encrypted_content=ciphertext,
        encryption_key_id=key_id
    )
    db_sensitive.add(user_msg)

    ciphertext, key_id = encrypt_content(reply)
    ai_msg = Conversation(
        session_id=counseling_session.id,
        user_id=uuid.UUID(current_user["user_id"]),
        role="assistant",
        message_type="text",
        encrypted_content=ciphertext,
        encryption_key_id=key_id
    )
    db_sensitive.add(ai_msg)

    await db_sensitive.flush()

    print("conversation_id =", user_msg.id)

    if is_crisis:
        await save_crisis_event(
            db=db_sensitive,
            user_id=current_user["user_id"],
            conversation_id=str(user_msg.id),
            severity=severity,
        )

    # 8. 감사 로그
    await log_sensitive(db_audit, current_user["user_id"], "CREATE", "CONVERSATION", user_msg.id)
    await log_sensitive(db_audit, current_user["user_id"], "CREATE", "CONVERSATION", ai_msg.id)

    await db_sensitive.commit()
    await db_audit.commit()

    return reply
