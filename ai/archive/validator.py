import re

def contains_foreign(text):

    pattern = r"[一-龯ぁ-ゔァ-ヴー々〆〤a-zA-Z]"

    return re.search(pattern, text) is not None
