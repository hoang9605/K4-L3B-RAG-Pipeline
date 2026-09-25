# Individual contribution report

## Thông tin

- Họ và tên: Lê Tuấn Đạt
- Mã học viên: 2A202602623
- Nhóm: Trike
- Repository/branch: https://github.com/hoang9605/K4-L3B-RAG-Pipeline (`feature/tuandat04`)

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Task 3 — OCR | Phát hiện Luật Du lịch 2017 là PDF scan (0 ký tự text); thêm OCR tiếng Việt EasyOCR làm fallback, cache kết quả vào `data/ocr_cache/` | `src/task3_convert_markdown.py`, `4d00133` | Done |
| Task 4 — Chunk/embed/index | Làm sạch markdown, parse title/URL, chunk recursive 800/120, embedding `gemini-embedding-001`, upsert Chroma idempotent + xoá chunk cũ; dùng lại vector khi nội dung không đổi | `src/task4_chunking_indexing.py`, `6f33dbf`, `ad91bd9` | Done |
| Task 5 — Dense search | Query Chroma, cosine similarity, chuẩn hoá metadata theo contract | `src/task5_semantic_search.py`, `6f33dbf` | Done |
| Task 10 — Generation | Reorder chống lost-in-the-middle, context đánh số map đúng `sources[n-1]`, dispatch Gemini/OpenAI/Anthropic, safe refusal, retry khi 429 theo phút | `src/task10_generation.py`, `bfed9a3`, `be0891c` | Done |
| Chatbot | Streamlit hiển thị answer, nguồn, method, score; highlight nguồn được cite | `app.py`, `621926b` | Done |
| Evaluation | Script ragas A/B (4 metric, evaluator khác generator), chạy và tổng hợp kết quả | `group_project/evaluation/run_evaluation.py`, `be0891c` | Done |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Chunk 800 ký tự, overlap 120, và dùng OCR thay vì bỏ văn bản scan.
   **Lý do/evidence:** Với chunk 500, nhiều "Điều" của văn bản luật bị cắt đôi. Với 800/120 được 481 chunk, câu định nghĩa trong Luật Du lịch nằm trọn một chunk. OCR giúp giữ được văn bản quan trọng nhất về pháp lý (98 "Điều", ~100KB text); test acceptance dữ liệu 2/3 → 3/3.
   **Trade-off:** Bản OCR còn lỗi dấu ("du Jịch") nên dense xếp chunk luật thấp hơn (Q0 hạng 10 dense). OCR mất ~10 phút trên CPU nên phải cache.

2. **Quyết định:** Đánh số context theo thứ hạng gốc (`citation`) trước khi reorder, trả `sources` theo score.
   **Lý do/evidence:** Contract yêu cầu `sources` sort giảm dần, còn reorder đảo vị trí chunk trong prompt. Nếu đánh số theo vị trí trong prompt thì `[n]` sẽ trỏ sai nguồn. Đã đối chiếu thủ công: "Giá vé phố cổ" cite [5] đúng chunk chứa 80.000/120.000 VND.
   **Trade-off:** Số Document trong prompt không theo thứ tự 1..5 liên tục; LLM vẫn cite đúng trên 18 câu eval.

## Kiểm thử và kết quả

- Test hoặc query tôi đã dùng: `pytest tests/test_contracts.py` (15/15), `pytest tests/test_acceptance.py`; query in-domain/out-of-domain ("Khu du lịch là gì?", "Công thức nấu phở bò"); `AppTest` chạy app headless; ragas A/B trên 18 câu golden.
- Kết quả trước/sau: chạy lại index 481/481 chunk dùng lại vector (0 lượt API, trước đó mỗi lần tốn 481 lượt và làm hết quota 1000/ngày). Evaluation cuối: Config A 0.845, Config B 0.873.
- Lỗi đã phát hiện và cách xử lý: (1) Gemini free tier hết quota embedding theo ngày → dùng lại vector cũ + báo lỗi rõ ràng; (2) `gemini-3.5-flash` chỉ 20 request/ngày → chuyển generator sang `gemini-3.5-flash-lite`, evaluator `gemini-3.1-flash-lite`; (3) lỗi 429 theo phút làm Q15 bị refusal sai trong eval → thêm retry theo `retryDelay`.

## Điều còn hạn chế

- Một hạn chế cụ thể của phần tôi làm: OCR Luật Du lịch còn lỗi dấu, làm giảm chất lượng dense search cho các câu hỏi luật (Q0 precision 0.2).
- Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện: thay bản scan bằng bản text chính thức của Luật Du lịch, rồi thêm reranker cross-encoder sau RRF (Recommendation 1 trong `RESULT.md`).

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 2026-09-25
- Tên thành viên: Lê Tuấn Đạt
