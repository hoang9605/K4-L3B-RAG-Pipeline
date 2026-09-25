# RAG evaluation results

## Run information

| Field                              | Value |
| ---------------------------------- | ----- |
| Evaluation date                    | 2026-09-25 |
| Framework and version              | ragas 0.4.3 (Faithfulness, ResponseRelevancy, LLMContextRecall, LLMContextPrecisionWithReference) |
| Evaluator model                    | gemini-3.1-flash-lite |
| Generator model                    | gemini-3.5-flash-lite (temperature 0.3, top_p 0.9) |
| Embedding model                    | gemini-embedding-001 (3072 chiều), ChromaDB cosine |
| Corpus version/commit              | `be0891c` — 3 văn bản legal + 6 bài news, 481 chunks (recursive 800/120) |
| Golden dataset size                | 18 câu (7 legal, 11 news) |
| `top_k`                            | 5 |
| Fallback threshold and calibration | 0.70 trên cosine gốc của dense; câu in-domain có best dense 0.77–0.87, câu out-of-domain 0.59–0.62 |

## Configurations

- **Config A — dense-only:** semantic search top 5 theo cosine similarity.
- **Config B — hybrid + RRF:** dense top 10 + BM25 top 10 (âm tiết + bigram, index cả bản dịch tiếng Việt của chunk tiếng Anh) → RRF k=2 → top 5.

Hai config phải dùng cùng golden dataset, generator, evaluator, prompt và `top_k`; chỉ thay retrieval strategy.

## Overall scores

| Metric            | Config A | Config B | Delta B−A |
| ----------------- | -------: | -------: | --------: |
| Faithfulness      |   0.9679 |   0.9458 |   −0.0221 |
| Answer relevance  |   0.8510 |   0.9067 |   +0.0557 |
| Context recall    |   0.8889 |   0.9444 |   +0.0555 |
| Context precision |   0.6708 |   0.6935 |   +0.0227 |
| **Average**       | **0.8447** | **0.8726** | **+0.0279** |

## A/B comparison

- Cấu hình tốt hơn: Config B (hybrid + RRF), trung bình 0.873 so với 0.845.
- Evidence: B trả lời được Q0 "Theo Luật Du lịch 2017, khu du lịch là gì?" mà A từ chối (recall 0 → 1.0) nhờ BM25 xếp chunk định nghĩa hạng 1–2; số câu từ chối giảm từ 2 xuống 1; precision tăng ở các câu thuật ngữ luật (Q1 0.5 → 1.0, Q2 0.58 → 0.75).
- Trade-off về latency/cost: A 4.61 s/câu, B 3.13 s/câu (chênh lệch do độ trễ API dao động); BM25 chạy local, không thêm API call mỗi query. B tốn thêm 12 lượt LLM một lần khi index để dịch 117 chunk tiếng Anh.

## Worst performers

|   # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage             | Root cause |
| --: | -------- | ------ | -----------: | --------: | -----: | --------: | ------------------------- | ---------- |
|   1 | Trải nghiệm Trung thu ở phố cổ Hội An khác biệt thế nào so với nơi khác? | A và B | 1.00 | 0.00 | 0.00 | 0.00 | retrieval | Đáp án nằm trong mục FAQ cuối bài; dense xếp hạng 15, BM25 hạng 2 nhưng RRF vẫn không đưa vào top 5 → hệ thống từ chối |
|   2 | Theo Luật Du lịch 2017, khu du lịch là gì? | B | 0.67 | 0.98 | 1.00 | 0.20 | retrieval/data | 4/5 context là QĐ UBND Hà Nội lặp cụm "khu du lịch"; chunk Luật Du lịch là bản OCR còn lỗi dấu nên dense xếp thấp |
|   3 | Những ai được miễn vé tham quan phố cổ Hội An? | B | 0.86 | 0.99 | 1.00 | 0.37 | generation | Context lẫn bài về đề xuất miễn phí cho đoàn khách; generator thêm "người có thu nhập thấp" không có trong nguồn |

## Recommendations

| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
| -------: | ------ | ------------------------------ | --------------- | ------------- |
|        1 | Thêm reranker cross-encoder sau RRF trên ~20 ứng viên | Q1 của bảng trên: BM25 tìm được hạng 2 nhưng RRF xếp sau; precision Q2, Q3 chỉ 0.2–0.37 | Tăng context precision và recall | So precision/recall trước và sau trên golden set |
|        2 | Lọc/boost theo tên văn bản nêu trong câu hỏi ("Luật Du lịch", "Hà Nội") | Q2: văn bản Hà Nội lấn át Luật Du lịch | Câu nêu rõ văn bản lấy đúng nguồn | Thêm 5 câu có tên văn bản, đo recall |
|        3 | Siết prompt chỉ liệt kê đúng đối tượng có trong nguồn; tạo dev set riêng để kiểm tra RRF k=2 | Q3: generator thêm ý ngoài nguồn; k=2 được chọn trên chính golden set | Faithfulness B ≥ A; kết quả đáng tin hơn | Chạy lại A/B trên dev set mới |

## Bonus experiments

| Experiment | Baseline | Metric delta | Latency/cost delta | Conclusion |
| ---------- | -------- | -----------: | -----------------: | ---------- |
| BM25 song ngữ (dịch chunk tiếng Anh sang tiếng Việt khi index) + RRF k=2 | Hybrid ban đầu (BM25 đơn ngữ, RRF k=60): average 0.7828 | +0.0898 (0.7828 → 0.8726) | +12 LLM call một lần khi index, 0 call thêm mỗi query | Giữ; hybrid vượt dense |
