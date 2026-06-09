import csv
import shutil
from pathlib import Path

mapping_file = Path("./data/mapping2.csv")

src_dir = Path("./data/transcripts")
dst_dir = Path("./data/transcripts_renamed")

dst_dir.mkdir(exist_ok=True)

with open(mapping_file, encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)

    for row in reader:
        old_path = src_dir / row["source_file"]
        new_path = dst_dir / row["rename"]

        if old_path.exists():
            shutil.copy2(old_path, new_path)
            print(f"OK: {new_path.name}")
        else:
            print(f"없음: {old_path.name}")

print("완료")

