"""
Task 1 — Thu thập tài liệu chính sách/quy định.

Hướng dẫn:
    1. Chọn chủ đề của nhóm.
    2. Tìm tối thiểu 3 tài liệu PDF/DOCX từ nguồn công khai.
    3. Lưu file gốc vào data/landing/legal/.
    4. Đặt tên không dấu và thể hiện đúng nội dung.

Ví dụ tài liệu: học phí, học bổng, ký túc xá, quy trình đăng ký.
Nếu website chặn crawler, hãy chọn nguồn công khai khác; không vượt WAF.
"""

from pathlib import Path


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"


def setup_directory() -> None:
    """Tạo thư mục lưu tài liệu gốc."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ready: {DATA_DIR}")


def download_documents() -> None:
    """Tài liệu được tải thủ công vào DATA_DIR; hàm này kiểm tra đủ số lượng."""
    files = [p for p in DATA_DIR.iterdir() if p.suffix.lower() in {".pdf", ".doc", ".docx"}]
    for path in files:
        print(f"Found: {path.name} ({path.stat().st_size // 1024} KB)")
    if len(files) < 3:
        raise SystemExit(f"Cần ít nhất 3 PDF/DOCX trong {DATA_DIR}, hiện có {len(files)}")


if __name__ == "__main__":
    setup_directory()
    download_documents()
