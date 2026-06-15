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
from models import Conversation, CounselingSession, Summary, Classification, ClassificationResult
from core.security import verify_access_token
from core.crypto import encrypt_content, decrypt_content
from routers.counseling import close_session_with_summary
from services.personas import normalize_persona, DEFAULT_PERSONA
from services.persona_service import build_persona_prompt
from services.audit_service import log_sensitive
from services.crisis_response import get_crisis_response_message, save_crisis_event
from services.crisis_tool_schema import CRISIS_TOOL, CRISIS_TOOL_INSTRUCTION

load_dotenv()

# ─────────────────────────────────────────
# Cerebras 클라이언트 (대화모델, OpenAI 호환)
# ─────────────────────────────────────────
groq_client = OpenAI(
    api_key=os.getenv("CEREBRAS_API_KEY"),
    base_url="https://api.cerebras.ai/v1",
)
# groq_client = OpenAI(
#     api_key=os.getenv("GROQ_API_KEY"),
#     base_url="https://api.groq.com/openai/v1",
# )
# ─────────────────────────────────────────
# 프롬프트 로드
# ─────────────────────────────────────────
AGENT_PROMPT_PATH = os.path.join(
    os.path.dirname(__file__), "../../ai/prompts/active/prompt_agent_prompt.txt"
)
with open(AGENT_PROMPT_PATH, "r", encoding="utf-8") as f:
    AGENT_PROMPT = f.read()

GENERAL_PROMPT_PATH = os.path.join(
    os.path.dirname(__file__), "../../ai/prompts/active/general_prompt.txt"
)
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
    # 한글·영문, 숫자·공백·기본 구두점만 허용, 나머지는 외국어로 감지
    # (한자, 일본어, 전각문자 등 모두 차단)
    pattern = r'[^가-힣ᄀ-ᇿ㄰-㆏A-Za-z0-9\s.,!?~\-\'"()…·%:/*]'
    return bool(re.search(pattern, text))


# ─────────────────────────────────────────
# 설문결과(classification) 로드 / 프롬프트 변환
# ─────────────────────────────────────────
async def load_classification_results(user_id, db_sensitive) -> list[dict]:
    """사용자의 '가장 최근' 설문(Classification)의 결과 행들을 dict 리스트로 반환.
    설문 이력이 없으면 빈 리스트.
    재대화/첫대화 모두 항상 최신 설문 상태를 반영하기 위해 user_id 기준으로 조회한다."""
    # 1) 해당 사용자의 가장 최근 설문 한 건 조회
    latest = await db_sensitive.execute(
        select(Classification)
        .where(
            Classification.user_id == uuid.UUID(user_id),
            Classification.deleted_at == None,
        )
        .order_by(Classification.created_at.desc())
        .limit(1)
    )
    latest_classification = latest.scalar()
    if not latest_classification:
        return []

    # 2) 그 설문의 카테고리별 결과 조회
    result = await db_sensitive.execute(
        select(ClassificationResult).where(
            ClassificationResult.classification_id == latest_classification.id
        )
    )
    return [
        {
            "category_code": r.category_code,
            "severity": r.severity,
            "total_score": r.total_score,
            "score_delta": r.score_delta,
        }
        for r in result.scalars().all()
    ]


def build_classification_prompt(results: list[dict]) -> str:
    """첫 대화(GENERAL_PROMPT)에 덧붙일 설문결과 텍스트 블록 생성.
    재대화(agent)는 구조화된 데이터를 직접 받으므로 이 함수를 쓰지 않는다."""
    if not results:
        return ""
    lines = [
        "[설문 결과]",
        "사용자의 사전 설문 결과다. 상담 태도·전략에만 반영하고 직접 언급하지 않는다:",
    ]
    for r in results:
        d = r.get("score_delta")
        trend = "" if d is None else f", 변화 {'+' if d > 0 else ''}{d}"
        score = r.get("total_score")
        score_text = score if score is not None else "미상"
        lines.append(
            f"- {r['category_code']}: 심각도 {r.get('severity') or '미상'}, "
            f"점수 {score_text}{trend}"
        )
    return "\n".join(lines)


# ─────────────────────────────────────────
# /chat 비즈니스 로직
# ─────────────────────────────────────────
async def process_chat(
    message: str,
    session_id: str,
    history: list[dict],
    persona: dict | None,
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
            CounselingSession.deleted_at == None,
        )
    )
    counseling_session = result.scalar()

    if not counseling_session:
        # 이전 세션 persona 복사 → 없으면 기본값.
        # 프론트가 보낸 persona가 있으면 그게 우선.
        last_result = await db_sensitive.execute(
            select(CounselingSession)
            .where(
                CounselingSession.user_id == uuid.UUID(current_user["user_id"]),
                CounselingSession.deleted_at == None,
            )
            .order_by(CounselingSession.started_at.desc())
            .limit(1)
        )
        last_session = last_result.scalar()
        inherited = normalize_persona(
            persona
            if persona is not None
            else (last_session.persona_type if last_session else None)
        )
        counseling_session = CounselingSession(
            id=uuid.UUID(session_id),
            user_id=uuid.UUID(current_user["user_id"]),
            persona_type=inherited,
            is_active=True,
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
        elapsed = datetime.now(timezone.utc) - last.created_at.replace(
            tzinfo=timezone.utc
        )
        if elapsed > timedelta(minutes=60):
            old_session_id = str(counseling_session.id)
            SESSION_PROMPT_CACHE.pop(old_session_id, None)
            # 옛 세션은 '닫기'만 동기로 빠르게 (요약 생성은 하지 않음)
            counseling_session.ended_at = datetime.now(timezone.utc)
            counseling_session.is_active = False
            await db_sensitive.flush()
            # 무거운 요약(/summary 호출)은 celery 백그라운드로 분리 → 응답 막지 않음
            from tasks.summary import summarize_session
            summarize_session.delay(old_session_id)
            # 새 세션 생성
            counseling_session = CounselingSession(
                user_id=uuid.UUID(current_user["user_id"]),
                persona_type=normalize_persona(
                    persona if persona is not None else counseling_session.persona_type
                ),
                is_active=True,
            )
            db_sensitive.add(counseling_session)
            await db_sensitive.flush()
            use_summary = True

    # 3.5 설문결과 로드 — 항상 사용자의 '최신' 설문 기준 (첫 대화 + 재대화 공통)
    classification_results = await load_classification_results(
        current_user["user_id"], db_sensitive
    )

    # 4. system_prompt 결정
    summary_result = await db_sensitive.execute(
        select(Summary)
        .where(
            Summary.user_id == uuid.UUID(current_user["user_id"]),
            Summary.deleted_at.is_(None),
        )
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
        # W2 복호화: main_complaint / next_session_notes는 BYTEA → 평문으로 풀어 Agent에 전달
        def _safe_decrypt(blob, kid):
            try:
                if blob is None:
                    return ""
                return decrypt_content(blob, kid)
            except Exception:
                return ""

        prompt_agent_input = {
            "nickname": current_user.get("nickname", "사용자"),
            "classification_results": classification_results,
            "summary": {
                "main_complaint": _safe_decrypt(
                    recent_summary.main_complaint_encrypted,
                    recent_summary.main_complaint_key_id,
                ),
                "core_topics": recent_summary.core_topics,
                "next_session_notes": _safe_decrypt(
                    recent_summary.next_session_notes_encrypted,
                    recent_summary.next_session_notes_key_id,
                ),

                "prompt_adjustment": recent_summary.prompt_adjustment,
                "important_memory": recent_summary.important_memory,
            },
            "risk_level": recent_summary.risk_level,
            "suicidal_mentioned": recent_summary.suicidal_mentioned,
            "persona_params": counseling_session.persona_type.get("params", {}),
            "ai_name": counseling_session.persona_type.get("name", "다온"),
            "talk_type": counseling_session.persona_type.get("talk_type", "존댓말"),
        }

        print("===== AGENT INPUT =====")
        print(json.dumps(prompt_agent_input, ensure_ascii=False, indent=2))
        agent_response = groq_client.chat.completions.create(
            model="gpt-oss-120b",
            messages=[
                {"role": "system", "content": AGENT_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(prompt_agent_input, ensure_ascii=False),
                },
            ],
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

        print("foreign =", contains_foreign(agent_result["system_prompt"]))

        system_content = GENERAL_PROMPT + "\n\n" + agent_result["system_prompt"]
        system_content += "\n\n" + CRISIS_TOOL_INSTRUCTION
        SESSION_PROMPT_CACHE[cache_key] = system_content
        print("=== system_prompt ===")  # Agent가 생성한 system_prompt 내용
        print(agent_result["system_prompt"])

    else:
        # 첫 대화: general_prompt 사용
        system_content = GENERAL_PROMPT
        classification_block = build_classification_prompt(classification_results)
        if classification_block:
            system_content += "\n\n" + classification_block
        system_content += "\n\n" + CRISIS_TOOL_INSTRUCTION
        SESSION_PROMPT_CACHE[cache_key] = system_content
        print("=== PROMPT: 첫 상담 - GENERAL_PROMPT 사용 ===")

    # ── 페르소나 프롬프트 (캐시 본체와 분리, 매 요청 재생성) ──
    # 프론트가 보낸 persona 우선, 없으면 DB 세션 값 사용.
    persona_source = persona if persona is not None else counseling_session.persona_type
    p = normalize_persona(persona_source)
    persona_prompt = build_persona_prompt(p)
    if persona_prompt:
        system_content += "\n\n" + persona_prompt

    # dirty-check: 프론트 persona가 DB와 다르면 UPDATE.
    # 브라우저 닫기·타임아웃으로 끝나도 마지막 값이 항상 DB에 남음.
    if persona is not None and counseling_session.persona_type != p:
        counseling_session.persona_type = p
        await db_sensitive.flush()

    # 5. Groq 응답 요청
    print("=== PROMPT 사용 ===")
    print(f"=== {system_content} ===")  # 최종 사용된 전체 프롬프트
    print("===================")
    messages_to_send = (
        [
            {"role": "system", "content": system_content},
            {"role": "user", "content": message},
        ]
        if use_summary
        else [
            {"role": "system", "content": system_content},
            *history,
            {"role": "user", "content": message},
        ]
    )

    response = groq_client.chat.completions.create(
        model="gpt-oss-120b",
        messages=messages_to_send,
        tools=[CRISIS_TOOL],
        tool_choice="auto",
    )
    message_obj = response.choices[0].message
    is_crisis = False

    print("===== TOOL CALLS =====")
    print(message_obj.tool_calls)
    print("======================")

    if message_obj.tool_calls:

        is_crisis = True

        args = json.loads(message_obj.tool_calls[0].function.arguments)

        severity = args["severity"]
        category = args["category"]
        reason = args["reason"]

        print("severity =", severity)
        print("category =", category)
        print("reason =", reason)

        print(f"=== CRISIS TOOL === " f"{severity} / {category} / {reason}")

        reply = get_crisis_response_message(severity)

    else:
        reply = response.choices[0].message.content

    print("=== REPLY CHECK ===", reply)  # 외국어 감지 필터 들어가기 전
    print("=== REPLY CHECK - 외국어감지 전 ===", contains_foreign(reply))

    # 6. 외국어 감지 (재생성 OFF - 테스트용)
    #    외국어가 감지돼도 재요청/폴백 없이 그대로 내보낸다.
    #    286번 줄 로그로 외국어 출현 여부는 계속 확인 가능.
    #    되돌릴 때는 아래 블록을 원래 "재요청 + 폴백" 코드로 복구하면 됨.
    if not is_crisis and contains_foreign(reply):
        pass   # 외국어 감지돼도 재요청/폴백 없이 그대로 출력

    print("=== REPLY CHECK (필터 후) ===", reply)

    # 7. 사용자/AI 메시지 저장
    ciphertext, key_id = encrypt_content(message)
    user_msg = Conversation(
        session_id=counseling_session.id,
        user_id=uuid.UUID(current_user["user_id"]),
        role="user",
        message_type="text",
        encrypted_content=ciphertext,
        encryption_key_id=key_id,
    )
    db_sensitive.add(user_msg)

    ciphertext, key_id = encrypt_content(reply)
    ai_msg = Conversation(
        session_id=counseling_session.id,
        user_id=uuid.UUID(current_user["user_id"]),
        role="assistant",
        message_type="text",
        encrypted_content=ciphertext,
        encryption_key_id=key_id,
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
    await log_sensitive(
        db_audit, current_user["user_id"], "CREATE", "CONVERSATION", user_msg.id
    )
    await log_sensitive(
        db_audit, current_user["user_id"], "CREATE", "CONVERSATION", ai_msg.id
    )

    await db_sensitive.commit()
    await db_audit.commit()

    return reply