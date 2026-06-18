# colab 서버로 이동

# from transformers import (
#     AutoTokenizer,
#     AutoModelForCausalLM,
#     BitsAndBytesConfig
# )

# from peft import PeftModel

# import torch

# from summary_generator import generate_summary


# model_name = "kakaocorp/kanana-nano-2.1b-instruct"

# bnb_config = BitsAndBytesConfig(
#     load_in_4bit=True,
#     bnb_4bit_use_double_quant=True,
#     bnb_4bit_quant_type="nf4",
#     bnb_4bit_compute_dtype=torch.float16
# )


# # base model
# base_model = AutoModelForCausalLM.from_pretrained(
#     model_name,
#     quantization_config=bnb_config,
#     device_map="auto"
# )

# # LoRA 연결
# model = PeftModel.from_pretrained(
#     base_model,
#     "./heartbeat_lora_v2_final"
# )

# tokenizer = AutoTokenizer.from_pretrained(
#     "./heartbeat_lora_v2_final"
# )


# test_transcript = """
# 상담사: 요즘 어떻게 지내고 계세요?
# 내담자: 그냥 하루하루 버티는 것 같아요.
# 상담사: 어떤 부분이 가장 힘드세요?
# 내담자: 회사 가는 게 너무 힘들고 아무것도 하기 싫어요.
# """


# result = generate_summary(
#     transcript=test_transcript,
#     model=model,
#     tokenizer=tokenizer
# )


# print(result)