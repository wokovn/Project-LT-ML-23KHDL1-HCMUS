import json
import re
from pathlib import Path

def merge_into_sentences(texts):
    """Ghép các đoạn text thành câu hoàn chỉnh, tách tại dấu . ! ?"""
    sentences = []
    current = ""

    # Nối tất cả text lại thành một chuỗi dài
    full_text = " ".join(t.strip() for t in texts if t.strip())

    # Tách câu tại dấu . ! ? (kể cả khi dấu nằm giữa đoạn)
    # Dùng regex: tách sau dấu câu kết thúc, giữ lại dấu câu
    parts = re.split(r'(?<=[.!?])\s+', full_text)

    for part in parts:
        part = part.strip()
        if part:
            sentences.append(part)

    return sentences


def build_corpus():
    transcripts_dir = Path("data/transcripts")
    corpus_dir = Path("data/raw_texts")
    corpus_dir.mkdir(parents=True, exist_ok=True)

    for json_file in transcripts_dir.glob("*.json"):
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        texts = [item["text"].strip() for item in data if "text" in item]
        sentences = merge_into_sentences(texts)

        output_file = corpus_dir / (json_file.stem + ".txt")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(sentences))

        print(f"Saved: {output_file} ({len(sentences)} câu)")


if __name__ == "__main__":
    build_corpus()