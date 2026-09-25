"""
Task 7 — Reciprocal Rank Fusion.

RRF gộp nhiều bảng xếp hạng mà không cộng trực tiếp cosine score với BM25
score. Công thức: RRF(d) = sum(1 / (k + rank)), rank bắt đầu từ 1.

Lưu ý: RRF score chỉ phản ánh thứ hạng, không dùng để quyết định fallback.
"""


def rerank_rrf(
    ranked_lists: list[list[dict]],
    top_k: int = 5,
    k: int = 60,
) -> list[dict]:
    """Fuse nhiều ranked lists và trả hybrid SearchResult."""
    scores: dict[str, float] = {}
    items: dict[str, dict] = {}
    for ranked_list in ranked_lists:
        for rank, item in enumerate(ranked_list, 1):
            item_id = item["id"]
            scores[item_id] = scores.get(item_id, 0.0) + 1 / (k + rank)
            items.setdefault(item_id, item)  # giữ bản của list đầu (dense)

    ranked_ids = sorted(scores, key=scores.get, reverse=True)
    return [
        {**items[item_id], "score": scores[item_id], "retrieval_method": "hybrid"}
        for item_id in ranked_ids[:top_k]
    ]


if __name__ == "__main__":
    from .task5_semantic_search import semantic_search
    from .task6_lexical_search import lexical_search

    query = "Giá vé tham quan phố cổ Hội An"
    fused = rerank_rrf([semantic_search(query, 10), lexical_search(query, 10)], top_k=5)
    for result in fused:
        print(round(result["score"], 4), result["id"], result["content"][:100])
