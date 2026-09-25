"""
Task 6 — Lexical search bằng BM25.

Dùng cùng corpus chunks với Task 5. BM25 phù hợp với từ khóa chính xác, mã tài
liệu và tên riêng. Output phải theo SearchResult và sort score giảm dần.
"""

import math
import re


CORPUS: list[dict] = []
_INDEX: tuple[list[dict] | None, object] = (None, None)


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

    return LuceneIdfBM25([tokenize(item["content"]) for item in corpus])


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
    for result in lexical_search("Giá vé tham quan phố cổ Hội An", top_k=3):
        print(round(result["score"], 2), result["id"], result["content"][:120])
