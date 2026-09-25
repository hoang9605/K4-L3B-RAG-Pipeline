# Individual contribution report

## Thông tin

- Họ và tên: Hoàng Văn Nam
- Mã học viên: 2A202602853
- Nhóm: Trike
- Repository/branch: https://github.com/hoang9605/K4-L3B-RAG-Pipeline

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Task 1 — Legal data | Tìm và tải 3 văn bản: Luật Du lịch 09/2017/QH14, QĐ UBND Đà Nẵng về TTHC du lịch (2026), QĐ UBND Hà Nội về quản lý khu du lịch (2024) | `data/landing/legal/`, `9aa669f`, PR #2 | Done |
| Task 3 — Chuẩn hóa Markdown | Convert PDF→MD bằng MarkItDown, JSON→MD có header title/source/ngày crawl; commit dữ liệu chuẩn hóa | `src/task3_convert_markdown.py`, `9f7706f`, `fb61e92`, PR #5, #6 | Done |
| Task 6 — BM25 | Tokenize âm tiết + bigram tiếng Việt; phát hiện và sửa IDF âm của BM25Okapi bằng IDF kiểu Lucene; BM25 đọc chung corpus chunk với Chroma | `src/task6_lexical_search.py` | Done |
| Task 7 — RRF | RRF `sum(1/(k+rank))`, k=60, dedupe theo ID, đánh dấu `hybrid` | `src/task7_reranking.py` | Done |
| Tích hợp repo | Review và merge PR #2–#6 vào `develop` | GitHub PR #2–#6 | Done |
| Evaluation — phân tích lỗi | Phân tích worst performers, root cause và recommendations | `group_project/evaluation/RESULT.md` | Done |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Thay IDF gốc của `BM25Okapi` bằng IDF kiểu Lucene `log(1 + (N-n+0.5)/(n+0.5))`.
   **Lý do/evidence:** Với IDF gốc, từ xuất hiện ở ≥ nửa số chunk ("du", "lịch", "hội", "an") có IDF ≤ 0; test contract `test_lexical_search_returns_bm25_contract` fail (kết quả rỗng). Sau khi sửa: test pass.
   **Trade-off:** Lệch nhẹ so với BM25 "chuẩn" trong sách; từ phổ biến vẫn đóng góp một ít điểm.

2. **Quyết định:** Token hóa BM25 bằng âm tiết + bigram (`phố_cổ`, `du_lịch`).
   **Lý do/evidence:** Tiếng Việt là ngôn ngữ đơn âm tiết; unigram khiến "phố cổ" khớp mọi chunk có "cổ". Bigram giúp khớp đúng cụm từ.
   **Trade-off:** Số token gấp đôi; không xử lý được từ bị lỗi dấu do OCR.

## Kiểm thử và kết quả

- Test đã dùng: `pytest tests/test_contracts.py -k "lexical or rrf"`, `pytest tests/test_acceptance.py -k "legal or news or standardized"`.
- Kết quả trước/sau: test BM25 fail → pass sau khi sửa IDF; dữ liệu chuẩn hóa 2/3 → 3/3 pass sau khi xử lý PDF scan.
- Lỗi phát hiện: câu hỏi tiếng Việt về giá vé không lấy được chunk tiếng Anh chứa "80.000 VND" (BM25 không khớp từ nào) → ghi vào worst performers.

## Điều còn hạn chế

- Hạn chế: BM25 không hiểu song ngữ; câu hỏi tiếng Việt không khớp được tài liệu tiếng Anh.
- Nếu có thêm thời gian: thêm query expansion VI→EN trước BM25 và đo A/B.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày:
- Tên thành viên:
