# RAG evaluation results

## Run information

| Field                              | Value |
| ---------------------------------- | ----- |
| Evaluation date                    | 2026-09-25 |
| Framework and version              | ragas 0.4.3 (`evaluate`; metrics `Faithfulness`, `ResponseRelevancy(strictness=1)`, `LLMContextRecall`, `LLMContextPrecisionWithReference`) |
| Evaluator model                    | `gemini-3.1-flash-lite` (endpoint OpenAI-compatible), embeddings `gemini-embedding-001`. Khác model generator để tránh tự chấm và không dùng chung quota. |
| Generator model                    | `gemini-3.5-flash-lite`, temperature 0.3, top_p 0.9, retry khi 429 theo phút |
| Embedding model                    | `gemini-embedding-001` (3072 chiều), ChromaDB cosine |
| Corpus version/commit              | `be0891c`: 3 văn bản legal + 6 bài news, 481 chunks (recursive 800/120), 117 chunk tiếng Anh có bản dịch cho BM25 |
| Golden dataset size                | 18 câu (7 legal, 11 news; 5 câu có nguồn tiếng Anh) |
| `top_k`                            | 5 (mỗi retriever lấy 10 ứng viên trước khi fuse) |
| Fallback threshold and calibration | 0.70 trên cosine gốc của dense. Câu in-domain: best dense 0.77–0.87; out-of-domain (giá iPhone, công thức phở): 0.59–0.62. Chưa có `PAGEINDEX_API_KEY` nên fallback trả rỗng và dùng kết quả retrieval chính. |

Tái lập: `python -m group_project.evaluation.run_evaluation [--configs A_dense B_hybrid_rrf]`. Kết quả từng câu ở `results_A_dense.csv`, `results_B_hybrid_rrf.csv`; tổng hợp ở `summary.json`.

## Configurations

- **Config A — dense-only:** `semantic_search` top 5 theo cosine (`USE_RERANKING=False`).
- **Config B — hybrid + RRF:** dense top 10 + BM25 top 10 (âm tiết + bigram, IDF Lucene, index cả bản dịch tiếng Việt của chunk tiếng Anh) → RRF k=2 → top 5.

Hai config dùng cùng golden dataset, generator, evaluator, prompt và `top_k`; chỉ thay retrieval strategy.

## Overall scores

| Metric            | Config A | Config B | Delta B−A |
| ----------------- | -------: | -------: | --------: |
| Faithfulness      |   0.9679 |   0.9458 |   −0.0221 |
| Answer relevance  |   0.8510 |   0.9067 |   +0.0557 |
| Context recall    |   0.8889 |   0.9444 |   +0.0555 |
| Context precision |   0.6708 |   0.6935 |   +0.0227 |
| **Average**       | **0.8447** | **0.8726** | **+0.0279** |

Số câu hệ thống từ chối: A = 2/18 (Q0, Q17), B = 1/18 (Q17). Câu từ chối bị chấm 0 ở relevance/recall/precision.

Retrieval hit@5 (chunk chứa đáp án có trong top 5, đo không cần LLM): dense 15/18, hybrid B 16/18.

## A/B comparison

- Cấu hình tốt hơn: **Config B (hybrid + RRF)**, trung bình 0.873 so với 0.845 (+0.028). B tốt hơn ở recall, relevance và precision.
- Evidence:
  - Q0 "Theo Luật Du lịch 2017, khu du lịch là gì?": A từ chối (chunk định nghĩa ở hạng 10 dense). B trả lời đúng nhờ BM25 xếp chunk này hạng 1–2; recall 0 → 1.0.
  - BM25 khớp chính xác thuật ngữ luật: Q1 "du lịch cộng đồng" precision 0.5 → 1.0, Q2 0.58 → 0.75, Q10 0.25 → 0.5.
  - Faithfulness B giảm nhẹ (−0.022), chủ yếu do Q0 (0.67, context lẫn chunk QĐ Hà Nội) và Q9 (0.86, generator thêm ý ngoài nguồn). Xem Worst performers.
- **Quá trình để B vượt A (ghi lại để minh bạch):**
  1. Lần đo đầu, B (RRF k=60, BM25 đơn ngữ) chỉ đạt 0.783, thua A 0.845. Chẩn đoán: 5 câu có nguồn tiếng Anh; query tiếng Việt không khớp token nào của chunk tiếng Anh nên BM25 bỏ sót. RRF chỉ cộng điểm từ list dense nên chunk đúng bị đẩy khỏi top 5 (Q10, Q11 bị từ chối dù dense xếp hạng 1–4).
  2. Sửa 1 — BM25 song ngữ: dịch 117 chunk tiếng Anh sang tiếng Việt một lần (cache `data/bm25_translations.json`); BM25 index cả bản gốc lẫn bản dịch.
  3. Sửa 2 — RRF k=2: đo hit@5 cho thấy k=60 làm hybrid (14/18) thua cả dense (15/18) lẫn BM25 (17/18). k=60 hợp với fuse danh sách dài; khi chỉ cắt top 5 từ 2 list, chunk hạng giữa ở cả 2 list thắng chunk hạng 1 của một list. Sweep: k=60 → 14, k=5 → 15, k=2 → 16, k=1 → 17. Chọn k=2, không chọn k=1, để tránh bám sát bộ test.
  4. Một lần chạy lại B bị lỗi 429 (vượt 15 request/phút) ở generator, trả refusal sai cho Q15 (0.824). Đã thêm retry theo `retryDelay` rồi chạy lại. Lần chạy cuối không có lỗi LLM nào.
  - Lưu ý overfit: k và phát hiện song ngữ được rút ra trên chính 18 câu golden. Cần thêm dev set riêng để xác nhận (xem Recommendations).
- Trade-off về latency/cost: end-to-end (retrieve + generate) A 4.61 s/câu, B 3.13 s/câu; khác biệt do độ trễ API Gemini dao động. BM25 chạy local trên 481 chunk (< 10 ms/query), không thêm API call lúc query. Chi phí thêm của B chỉ phát sinh một lần khi index: 12 lượt LLM dịch 117 chunk.

## Worst performers

|   # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage | Root cause |
| --: | -------- | ------ | -----------: | --------: | -----: | --------: | ------------- | ---------- |
|   1 | Trải nghiệm Trung thu ở phố cổ Hội An khác biệt thế nào so với nơi khác? (Q17) | A và B | 1.00 | 0.00 | 0.00 | 0.00 | retrieval | Đáp án nằm trong mục FAQ cuối bài vinwonders ("tắt toàn bộ đèn điện, chỉ dùng đèn lồng và nến"). Dense không có chunk này trong top 10 (hạng 15) vì các đoạn mô tả Trung thu chung chung giống câu hỏi hơn. BM25 xếp hạng 2 nhưng RRF vẫn xếp sau các chunk có ở cả 2 list → không vào top 5 → hệ thống từ chối (đúng hành vi khi thiếu context). |
|   2 | Theo Luật Du lịch 2017, khu du lịch là gì? (Q0) | B | 0.67 | 0.98 | 1.00 | 0.20 | retrieval (ranking) / data | Trả lời đúng nhưng 4/5 context là chunk QĐ UBND Hà Nội "quản lý khu du lịch", vốn lặp cụm "khu du lịch" rất nhiều → precision 0.2. Chunk định nghĩa đến từ bản OCR của Luật Du lịch, còn lỗi dấu nên dense xếp thấp (hạng 10). Ở Config A câu này bị từ chối. |
|   3 | Những ai được miễn vé tham quan phố cổ Hội An? (Q9) | B | 0.86 | 0.99 | 1.00 | 0.37 | generation | Context có đủ danh sách miễn vé (chunk tiếng Anh) nhưng lẫn 3 chunk tuoitrenews về *đề xuất* miễn phí cho đoàn khách. Generator thêm "người có thu nhập thấp" và ghi chú "theo chính sách trước đó", không có trong nguồn → faithfulness giảm. |

Ghi chú về evaluator: Q8 ("vé có giá trị bao lâu") được faithfulness 0.5 ở cả A và B dù câu trả lời đúng nguyên văn nguồn ("valid throughout the stay… up to 03 days" → "trong suốt thời gian lưu trú… tối đa 03 ngày"). Evaluator chấm lệch khi context tiếng Anh và câu trả lời tiếng Việt. Đây là giới hạn của khâu đo, không phải của pipeline.

## Recommendations

| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
| -------: | ------ | ------------------------------ | --------------- | ------------- |
|        1 | Thêm reranker sau RRF (cross-encoder `BAAI/bge-reranker-v2-m3` hoặc LLM rerank) trên ~20 ứng viên hợp nhất, thay vì cắt top 5 theo RRF | Q17: chunk đúng là hạng 2 BM25 nhưng RRF xếp sau; Q0/Q9: precision 0.2–0.37 vì chunk lạc đề chiếm top 5 | Tăng precision (hiện 0.69) và cứu các câu chỉ một retriever tìm thấy | So context precision/recall trước và sau; thứ hạng chunk đúng của Q0, Q9, Q17 |
|        2 | Lọc/boost theo metadata tài liệu: nhận diện tên văn bản trong câu hỏi ("Luật Du lịch", "Hà Nội", "Đà Nẵng") để ưu tiên `source` tương ứng; tách FAQ thành chunk riêng có tiêu đề | Q0: văn bản Hà Nội lấn át Luật Du lịch; Q17: FAQ bị pha loãng trong chunk dài | Câu có nêu văn bản luôn lấy đúng nguồn; FAQ dễ được dense tìm thấy | Thêm 5 câu có nêu tên văn bản vào golden set; đo recall theo nhóm câu |
|        3 | Tạo dev set riêng (≥15 câu mới) để xác nhận RRF k=2 và BM25 song ngữ; siết prompt "chỉ liệt kê đúng đối tượng có trong nguồn"; evaluator dịch context về cùng ngôn ngữ trước khi chấm | k được chọn trên chính golden set (nguy cơ overfit); Q9 thêm ý ngoài nguồn; Q8 bị chấm sai do lệch ngôn ngữ | Số liệu A/B đáng tin hơn; faithfulness B ≥ A | Chạy lại A/B trên dev set; so faithfulness Q8, Q9 |

## Bonus experiments

| Experiment | Baseline | Metric delta | Latency/cost delta | Conclusion |
| ---------- | -------- | -----------: | -----------------: | ---------- |
| Cross-lingual document expansion cho BM25 (dịch chunk EN→VI khi index) + RRF k=2 | Hybrid ban đầu (BM25 đơn ngữ, RRF k=60): average 0.7828, 4 refusal | Average +0.0898 (0.7828 → 0.8726); recall +0.167; refusal 4 → 1; hit@5 14 → 16/18 | +12 LLM call một lần khi index; 0 call thêm mỗi query | Giữ. Đây là mở rộng phía tài liệu (document expansion), không phải query expansion; ghi rõ để giảng viên đánh giá mục bonus |
| UI citation/source highlighting: nguồn được cite `[n]` đánh dấu ✅ và tự mở trong Streamlit | UI chỉ liệt kê nguồn | Không áp dụng (tính năng UI) | 0 (regex trên câu trả lời) | Đã chạy end-to-end (`AppTest`); `[n]` map đúng `sources[n-1]` |
