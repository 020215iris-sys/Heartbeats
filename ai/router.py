def route_prompt(user_input):

    text = user_input.lower()

    if "죽고 싶" in text or "죽고싶" in text:
        return "emergency_response_prompt"

    elif "포기" in text or "더는" in text:
        return "escalation_prompt"

    elif "우울" in text or "힘들" in text:
        return "emotional_prompt"
    
    elif (
    "그만하고 싶" in text
    or "사라지고 싶" in text
    or "없어지고 싶" in text
    or "다 싫" in text
    or "더는" in text
    or "그만하고싶" in text
    or "없어지고싶" in text
    or "그만할" in text
    or "무리" in text
    or "한계" in text
        ):
        return "stabilization_prompt"
    

    return "general_prompt"