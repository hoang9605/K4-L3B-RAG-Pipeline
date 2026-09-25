# Individual contribution report

## Thông tin

- Họ và tên: Nguyễn Hải Hoàng
- Mã học viên: 2A202602489
- Nhóm: Trike
- Repository/branch: https://github.com/hoang9605/K4-L3B-RAG-Pipeline

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Repo nhóm | Tạo repository nhóm, nhánh `develop` và luồng PR | GitHub `hoang9605/K4-L3B-RAG-Pipeline` | Done |
| Task 1 — Legal | Chuẩn bị script thu thập tài liệu | `src/task1_collect_legal_docs.py`, `7234dd6`, PR #1 | Done |
| Task 2 — Crawler | Crawler Crawl4AI dùng chung một `AsyncWebCrawler`; sau đó thêm kiểm tra lỗi (404, Cloudflare, nội dung ngắn), bỏ `nav/header/footer`, loại link quảng cáo/vé máy bay | `src/task2_crawl_news.py`, `e5d8a58`, PR #3 | Done |
| Task 8 — PageIndex | Upload PDF, cache doc ID, query có timeout 30s; trả `[]` khi thiếu API key để pipeline không crash | `src/task8_pageindex_vectorless.py` | Partial (chưa có API key để chạy thật) |
| Task 9 — Retrieval pipeline | Dense + BM25 → RRF đúng một lần; fallback theo cosine gốc của dense; calibrate threshold | `src/task9_retrieval_pipeline.py` | Done |
| Golden dataset | Viết và đối chiếu 18 câu hỏi với tài liệu gốc (7 legal, 11 news) | `group_project/evaluation/golden_dataset.json` | Done |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Đặt ngưỡng fallback `SCORE_THRESHOLD = 0.70` trên cosine gốc của dense search (không dùng RRF score).
   **Lý do/evidence:** Thử 4 câu in-domain được best dense 0.77–0.87, 2 câu out-of-domain (giá iPhone, công thức phở) được 0.59–0.62; 0.70 nằm giữa hai nhóm. RRF score (~0.03) chỉ phản ánh thứ hạng nên không so với ngưỡng được.
   **Trade-off:** Mới calibrate trên số ít câu; câu in-domain diễn đạt lạ có thể rơi dưới ngưỡng.

2. **Quyết định:** Khi thiếu `PAGEINDEX_API_KEY` hoặc PageIndex lỗi, `pageindex_search` trả `[]` và pipeline dùng kết quả hybrid.
   **Lý do/evidence:** Contract yêu cầu provider lỗi không làm UI crash; test `test_retrieve_survives_fallback_provider_error` pass.
   **Trade-off:** Câu ngoài domain vẫn đi tiếp tới LLM với context hybrid kém liên quan; an toàn nhờ prompt từ chối ở Task 10.

## Kiểm thử và kết quả

- Test đã dùng: `pytest tests/test_contracts.py -k retrieve` (3 test fallback/RRF), chạy crawler và mở từng JSON kiểm tra.
- Kết quả trước/sau: crawl lần đầu 7 URL chỉ 4 bài dùng được (404, Cloudflare, rỗng) → 6/6 bài hợp lệ sau khi thêm kiểm tra lỗi.
- Lỗi phát hiện: câu "Theo Luật Du lịch 2017, khu du lịch là gì?" không lấy được chunk định nghĩa vì QĐ Hà Nội chiếm top-5 → hệ thống từ chối (đúng hành vi, nhưng recall thấp).

## Điều còn hạn chế

- Hạn chế: Task 8 chưa chạy với API thật; phần parse response PageIndex chưa kiểm chứng.
- Nếu có thêm thời gian: lấy PageIndex key, chạy `upload_documents()` và hiệu chỉnh parser theo response thật.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 25/9/2026
- Tên thành viên: Nguyễn Hải Hoàng
