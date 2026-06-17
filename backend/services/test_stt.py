from faster_whisper import WhisperModel

model = WhisperModel(
    "small",
    device="cpu",
    compute_type="int8"
)

segments, info = model.transcribe(
    "테스트음원333.wav",
    language="ko"
)

print("language:", info.language)

for segment in segments:
    print(segment.text)


import time

start = time.time()

segments, _ = model.transcribe(
    "테스트음원333.wav",
    language="ko"
)

print("STT TIME =", round(time.time() - start, 2))