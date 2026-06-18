from faster_whisper import WhisperModel


model = WhisperModel(
    "small",
    device="cpu",
    compute_type="int8"
)

def transcribe_audio(audio_path: str) -> str:
    segments, info = model.transcribe(
        audio_path,
        language="ko",
        vad_filter=True
    )

    segments = list(segments)

    print("segment count =", len(segments))

    for seg in segments:
        print("SEG:", repr(seg.text))

    text = "".join(
        seg.text
        for seg in segments
    ).strip()

    print("result =", repr(text))

    return text