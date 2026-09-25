"""
Task 3 — Chuẩn hóa dữ liệu sang Markdown.

Hướng dẫn:
    1. Dùng MarkItDown để convert PDF/DOCX.
    2. Đọc JSON và giữ metadata ở đầu file Markdown.
    3. Giữ cấu trúc thư mục legal/ và news/.
    4. Không tạo file rỗng hoặc file trùng khi chạy lại.

Cài đặt:
    Dependency MarkItDown đã được khai báo trong pyproject.toml.
    
-> Hoặc dùng công cụ nào bạn quen khác Markitdown
"""

from pathlib import Path


LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"
# OCR chậm (~17s/trang trên CPU) nên cache kết quả và commit để cả nhóm dùng lại.
OCR_CACHE_DIR = Path(__file__).parent.parent / "data" / "ocr_cache"


def ocr_pdf(path: Path) -> str:
    """OCR PDF scan bằng EasyOCR tiếng Việt; dùng cache nếu đã OCR trước đó."""
    cache = OCR_CACHE_DIR / f"{path.stem}.txt"
    if cache.exists():
        return cache.read_text(encoding="utf-8")

    import easyocr
    import numpy as np
    import pypdfium2 as pdfium

    reader = easyocr.Reader(["vi"], gpu=False, verbose=False)
    pdf = pdfium.PdfDocument(str(path))
    pages = []
    for index in range(len(pdf)):
        print(f"  OCR {path.name}: page {index + 1}/{len(pdf)}")
        image = np.array(pdf[index].render(scale=2).to_pil())
        pages.append("\n".join(reader.readtext(image, detail=0, paragraph=True)))
    text = "\n\n".join(pages).strip()
    OCR_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache.write_text(text, encoding="utf-8")
    return text


def prepare_output_dir(name: str) -> Path:
    """Tạo thư mục output và xoá .md cũ để chạy lại không để sót file thừa."""
    output_dir = OUTPUT_DIR / name
    output_dir.mkdir(parents=True, exist_ok=True)
    for old in output_dir.glob("*.md"):
        old.unlink()
    return output_dir


def convert_legal_docs() -> None:
    from markitdown import MarkItDown
    legal_dir = LANDING_DIR / "legal"
    output_dir = prepare_output_dir("legal")
    converter = MarkItDown()
    for path in legal_dir.iterdir():
        if path.suffix.lower() in {".pdf", ".doc", ".docx"}:
            text = converter.convert(str(path)).text_content.strip()
            if not text and path.suffix.lower() == ".pdf":
                # PDF scan (chỉ có ảnh) không có lớp text -> OCR.
                print(f"No text layer, running OCR: {path.name}")
                text = ocr_pdf(path)
            if not text:
                print(f"Skipped (no text): {path.name}")
                continue
            (output_dir / f"{path.stem}.md").write_text(text, encoding="utf-8")


def convert_news_articles() -> None:
    import json
    news_dir = LANDING_DIR / "news"
    output_dir = prepare_output_dir("news")
    for path in news_dir.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        header = (
            f"# {data['title']}\n\n"
            f"**Source:** {data['url']}\n\n"
            f"**Crawled:** {data['date_crawled']}\n\n---\n\n"
        )
        (output_dir / f"{path.stem}.md").write_text(
            header + data["content_markdown"], encoding="utf-8"
        )


def convert_all() -> None:
    """Convert toàn bộ dữ liệu landing."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    convert_legal_docs()
    convert_news_articles()
    print(f"Saved Markdown to: {OUTPUT_DIR}")


if __name__ == "__main__":
    convert_all()
