# services/persona_service.py

def build_persona_prompt(persona: dict) -> str:
    """
    v2 persona dict → system prompt 문자열 변환.

    Args:
        persona: normalize_persona()를 통과한 v2 dict.
                 {"name": ..., "talk_type": ..., "params": {...}, ...}

    말수: LLM 해석에 맡기지 않고 코드에서 문장 수 제약으로 변환.
    따듯함·공감도·전문성: 1/5/10 앵커 정의 + 숫자 전달
        → 모델이 양 끝점 사이를 보간. 6과 7 차이는 미미하지만 2와 8은 체감됨.
    충돌 우선순위: 말수(문장 수 제약)가 다른 항목보다 우선.
    """
    if not persona:
        return ""

    lines = ["[상담사 페르소나]"]

    # ── 이름 ──
    name = persona.get("name", "")
    if name:
        lines.append(f"- 당신의 이름은 '{name}'입니다. 사용자가 이름을 물으면 이 이름으로 답하세요.")

    # ── 말투 ──
    talk_type = persona.get("talk_type", "존댓말")
    if talk_type == "반말":
        lines.append("- 사용자에게 친근한 반말로 대화합니다. 존댓말을 절대 섞지 않습니다.")
    else:
        lines.append("- 사용자에게 정중한 존댓말로 대화합니다. 반말을 섞지 않습니다.")

    params = persona.get("params")
    if not params:
        return "\n".join(lines)

    # ── 말수 → 측정 가능한 문장 수 제약 ──
    # 말수 1 → 최대 1문장, 10 → 최대 5문장
    mal_su = params.get("말수")
    if mal_su is not None:
        max_sentences = max(1, round(int(mal_su) * 0.5))
        lines.append(f"- 응답은 최대 {max_sentences}문장으로 제한합니다. 넘지 마세요.")

    # ── 앵커 정의 + 숫자 전달 ──
    # 콤마 없으면 Python이 문자열 자동 연결 → 한 줄로 뭉개짐. 각 항목 별도 append.
    lines.append("")
    lines.append("[스타일 점수] 각 항목은 1~10이며 아래 기준으로 해석하세요:")

    dduk = params.get("따듯함")
    if dduk is not None:
        lines.append(
            f"- 따듯함 {dduk}/10"
            " (1=사무적·건조한 어조 / 5=정중하지만 담백 / 10=매우 다정하고 부드러운 어조)"
        )

    gong = params.get("공감도")
    if gong is not None:
        lines.append(
            f"- 공감도 {gong}/10"
            " (1=감정 언급 없이 내용만 반응 / 5=감정을 한 번 짚고 넘어감 / 10=매 응답마다 감정을 먼저 반영)"
        )

    jun = params.get("전문성")
    if jun is not None:
        lines.append(
            f"- 전문성 {jun}/10"
            " (1=일상 언어만 사용 / 5=쉬운 심리 개념 가끔 소개 / 10=전문 개념을 적극 활용해 설명)"
        )

    lines.append("- 지시가 충돌하면 말수(문장 수) 제약을 가장 우선합니다.")

    return "\n".join(lines)