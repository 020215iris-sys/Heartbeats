from router import route_prompt
from llm import generate_response
from validator import contains_foreign


def load_prompt(prompt_name):

    path = f"./prompts/{prompt_name}.txt"

    with open(path, "r", encoding="utf-8") as f:
        return f.read()
    
conversation_history = []


fallback_map = {
    "general_prompt":
        "오늘은 유난히 지친 하루였나 보네요.",

    "emotional_prompt":
        "계속 마음이 무거운 상태처럼 들리네요.",

    "stabilization_prompt":
        "지금은 많이 버거운 상태처럼 들려요.",

    "emergency_response":
        "지금 혼자 감당하기 힘든 상태일 수 있어요."
}

while True:

    user_input = input("USER: ")

    if user_input.lower() == "exit":

        summary_prompt = load_prompt("summary_prompt")

        conversation_text = "\n".join(conversation_history)

        state = { "selected_prompt_key": prompt_key } 
        
        summary_input = f"""
        [SYSTEM STATE]
        {state}
        
        [CONVERSATION]
        {conversation_text}
        """

        summary = generate_response(
            summary_prompt,
            conversation_text
        )

        print("\n===== SUMMARY =====")
        print(summary)

        break

    conversation_history.append(f"USER: {user_input}")


    prompt_key = route_prompt(user_input)

    print("SELECTED:", prompt_key)

    system_prompt = load_prompt(prompt_key)

    response = generate_response(system_prompt, user_input)

    if contains_foreign(response): 
        response = generate_response( 
            system_prompt + "\n한국어로만 자연스럽게 다시 응답하세요."
            , user_input )
        
        if contains_foreign(response): 
            response = fallback_map[prompt_key]

    conversation_history.append(f"AI: {response}")

    print("AI:", response)