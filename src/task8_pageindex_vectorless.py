"""
Task 8 — PageIndex vectorless fallback.

Hướng dẫn:
    1. Đọc PAGEINDEX_API_KEY từ .env.
    2. Upload tài liệu ở định dạng PageIndex hỗ trợ.
    3. Cache document IDs để không upload lại.
    4. Parse kết quả thành SearchResult có method pageindex.

PageIndex là dịch vụ ngoài: cần timeout và xử lý lỗi để pipeline không crash.
Không có PAGEINDEX_API_KEY -> pageindex_search trả [] và pipeline dùng hybrid.
"""

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "").strip()
ROOT = Path(__file__).parent.parent
STANDARDIZED_DIR = ROOT / "data" / "standardized"
LEGAL_PDF_DIR = ROOT / "data" / "landing" / "legal"  # PageIndex chỉ nhận PDF
DOC_IDS_FILE = ROOT / "pageindex_doc_ids.json"  # đã có trong .gitignore
POLL_SECONDS = 2
TIMEOUT_SECONDS = 30


def _client():
    from pageindex import PageIndexClient
    return PageIndexClient(api_key=PAGEINDEX_API_KEY)


def _load_doc_ids() -> dict[str, str]:
    if DOC_IDS_FILE.exists():
        return json.loads(DOC_IDS_FILE.read_text(encoding="utf-8"))
    return {}


def upload_documents() -> None:
    """Upload tài liệu và lưu document IDs để tái sử dụng."""
    if not PAGEINDEX_API_KEY:
        print("PAGEINDEX_API_KEY chưa được cấu hình, bỏ qua upload.")
        return
    doc_ids = _load_doc_ids()
    client = _client()
    for path in sorted(LEGAL_PDF_DIR.glob("*.pdf")):
        if path.name in doc_ids:
            continue
        doc_ids[path.name] = client.submit_document(str(path))["doc_id"]
        DOC_IDS_FILE.write_text(json.dumps(doc_ids, indent=2), encoding="utf-8")
        print(f"Uploaded {path.name} -> {doc_ids[path.name]}")


def _query_document(client, doc_id: str, query: str) -> list[dict]:
    retrieval_id = client.submit_query(doc_id, query)["retrieval_id"]
    deadline = time.time() + TIMEOUT_SECONDS
    while time.time() < deadline:
        result = client.get_retrieval(retrieval_id)
        if result.get("status") == "completed":
            # ponytail: field names theo tài liệu PageIndex, chưa chạy thử được
            # vì nhóm chưa có API key -> in response thật và chỉnh nếu khác.
            return result.get("retrieved_nodes", [])
        time.sleep(POLL_SECONDS)
    raise TimeoutError(f"PageIndex retrieval timeout ({TIMEOUT_SECONDS}s)")


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """Trả về pageindex SearchResult."""
    doc_ids = _load_doc_ids()
    if not PAGEINDEX_API_KEY or not doc_ids:
        return []
    client = _client()
    results = []
    for source, doc_id in doc_ids.items():
        for node in _query_document(client, doc_id, query):
            content = "\n".join(
                item.get("relevant_content", "") for item in node.get("relevant_contents", [])
            ).strip()
            if not content:
                continue
            results.append({
                "id": f"pageindex::{doc_id}::{node.get('node_id', len(results))}",
                "content": content,
                "metadata": {
                    "source": source,
                    "title": node.get("title") or source,
                    "doc_type": "legal",
                    "url": None,
                    "chunk_index": len(results),
                },
                "retrieval_method": "pageindex",
            })
    # API không trả score -> gán score giảm dần theo thứ tự trả về.
    results = results[:top_k]
    for rank, item in enumerate(results):
        item["score"] = 1.0 / (rank + 1)
    return results


if __name__ == "__main__":
    upload_documents()
