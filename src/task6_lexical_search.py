"""
Task 6 — Lexical search bằng BM25.

Dùng cùng corpus chunks với Task 5. BM25 phù hợp với từ khóa chính xác, mã tài
liệu và tên riêng. Output phải theo SearchResult và sort score giảm dần.

Corpus song ngữ: query tiếng Việt không khớp token nào của chunk tiếng Anh, nên
RRF đẩy các chunk này ra khỏi top-k (eval Q10, Q11). Mỗi chunk tiếng Anh được
dịch sang tiếng Việt MỘT LẦN (build_translations) và cache vào file; BM25 index
cả bản gốc + bản dịch. Nội dung trả về/đưa cho LLM vẫn là bản gốc.
"""

import hashlib
import json
import math
import re
from pathlib import Path


CORPUS: list[dict] = []
_INDEX: tuple[list[dict] | None, object] = (None, None)
TRANSLATIONS_FILE = Path(__file__).parent.parent / "data" / "bm25_translations.json"
TRANSLATE_BATCH = 10
VI_CHARS = set("ăâđêôơưàáảãạằắẳẵặầấẩẫậèéẻẽẹềếểễệìíỉĩịòóỏõọồốổỗộờớởỡợùúủũụừứửữựỳýỷỹỵ")


def _content_key(text: str) -> str:
    # Key theo nội dung -> chunk đổi nội dung thì bản dịch cũ tự bị bỏ qua.
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def is_english(text: str) -> bool:
    letters = re.findall(r"[^\W\d_]", text.lower())
    return len(letters) > 50 and sum(ch in VI_CHARS for ch in letters) / len(letters) < 0.02


def load_translations() -> dict[str, str]:
    if TRANSLATIONS_FILE.exists():
        return json.loads(TRANSLATIONS_FILE.read_text(encoding="utf-8"))
    return {}


def build_translations() -> None:
    """Dịch các chunk tiếng Anh sang tiếng Việt cho BM25 (chạy 1 lần sau Task 4)."""
    from .task10_generation import call_llm

    cache = load_translations()
    todo = [c for c in load_corpus() if is_english(c["content"]) and _content_key(c["content"]) not in cache]
    print(f"Translating {len(todo)} English chunks")
    separator = "<<<SPLIT>>>"
    system = (
        "Dịch từng đoạn tiếng Anh sang tiếng Việt, giữ nguyên số, tên riêng. "
        f"Các đoạn input ngăn cách bởi dòng {separator}; output giữ đúng số đoạn, "
        f"đúng thứ tự, ngăn cách bởi dòng {separator}, không thêm gì khác."
    )
    for start in range(0, len(todo), TRANSLATE_BATCH):
        batch = todo[start:start + TRANSLATE_BATCH]
        try:
            raw = call_llm(system, f"\n{separator}\n".join(c["content"] for c in batch))
        except Exception as error:
            print(f"  skip batch {start}: {error}")
            continue
        translated = [part.strip() for part in raw.split(separator)]
        if len(translated) != len(batch):
            print(f"  skip batch {start}: got {len(translated)} for {len(batch)}")
            continue
        for chunk, text in zip(batch, translated):
            cache[_content_key(chunk["content"])] = text
        TRANSLATIONS_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  {min(start + TRANSLATE_BATCH, len(todo))}/{len(todo)}")


def tokenize(text: str) -> list[str]:
    """Âm tiết tiếng Việt + bigram: "phố cổ" khớp cụm, không chỉ từng âm tiết."""
    syllables = re.findall(r"\w+", text.lower())
    return syllables + [f"{a}_{b}" for a, b in zip(syllables, syllables[1:])]


def load_corpus() -> list[dict]:
    """Đọc đúng các chunk đã index trong Chroma để BM25 và dense chung corpus."""
    from .task4_chunking_indexing import get_collection
    data = get_collection().get(include=["documents", "metadatas"])
    return [
        {
            "id": item_id,
            "content": content,
            "metadata": {**metadata, "url": metadata.get("url") or None},
        }
        for item_id, content, metadata in zip(data["ids"], data["documents"], data["metadatas"])
    ]


def build_bm25_index(corpus: list[dict]):
    """Tạo BM25 index từ cùng corpus chunks của Task 4."""
    from rank_bm25 import BM25Okapi

    class LuceneIdfBM25(BM25Okapi):
        # IDF gốc của Okapi <= 0 với từ có ở >= nửa số chunk ("du", "lịch", "hội")
        # -> từ đó mất tác dụng. IDF kiểu Lucene luôn dương.
        def _calc_idf(self, nd):
            self.idf = {
                word: math.log(1 + (self.corpus_size - freq + 0.5) / (freq + 0.5))
                for word, freq in nd.items()
            }

    translations = load_translations()
    return LuceneIdfBM25([
        tokenize(item["content"] + " " + translations.get(_content_key(item["content"]), ""))
        for item in corpus
    ])


def _get_index():
    global CORPUS, _INDEX
    if not CORPUS:
        CORPUS = load_corpus()
    if _INDEX[0] is not CORPUS:  # CORPUS đổi (vd. test monkeypatch) -> build lại
        _INDEX = (CORPUS, build_bm25_index(CORPUS))
    return CORPUS, _INDEX[1]


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Trả về BM25 SearchResult theo score giảm dần."""
    corpus, bm25 = _get_index()
    if not corpus:
        return []
    scores = bm25.get_scores(tokenize(query))
    ranked = sorted(range(len(corpus)), key=lambda i: scores[i], reverse=True)
    return [
        {
            "id": corpus[i]["id"],
            "content": corpus[i]["content"],
            "score": float(scores[i]),
            "metadata": corpus[i]["metadata"],
            "retrieval_method": "bm25",
        }
        for i in ranked[:top_k]
        if scores[i] > 0
    ]


if __name__ == "__main__":
    build_translations()
    for result in lexical_search("Giá vé tham quan phố cổ Hội An", top_k=3):
        print(round(result["score"], 2), result["id"], result["content"][:120])
