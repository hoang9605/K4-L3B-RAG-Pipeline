"""
Task 7 — Reciprocal Rank Fusion.

RRF gộp nhiều bảng xếp hạng mà không cộng trực tiếp cosine score với BM25
score. Công thức: RRF(d) = sum(1 / (k + rank)), rank bắt đầu từ 1.

Lưu ý: RRF score chỉ phản ánh thứ hạng, không dùng để quyết định fallback.

k=60 (Cormack) hợp với fuse danh sách dài; ở đây chỉ cắt top-5 từ 2 list x 10,
k=60 khiến chunk hạng giữa ở cả 2 list thắng chunk hạng 1 của một list. Đo hit@5
trên golden set (18 câu): k=60 -> 14/18, k=5 -> 15/18, k=2 -> 16/18, dense 15/18.
"""

# ponytail: k chọn trên chính golden set (chưa có dev set riêng) -> có thể overfit;
# thêm câu hỏi mới rồi đo lại hit@5 trước khi đổi.
RRF_K = 2


def rerank_rrf(
    ranked_lists: list[list[dict]],
    top_k: int = 5,
    k: int = RRF_K,
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
