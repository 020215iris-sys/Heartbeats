def select_strategy(risk_level, core_topics):

    if risk_level == "high":
        return "crisis"

    if "불안" in core_topics:
        return "anxiety"

    if "우울" in core_topics:
        return "depression"

    return "general"