"""
Task 4 — Chunking, embedding và indexing.

Hướng dẫn:
    1. Đọc toàn bộ Markdown trong data/standardized/.
    2. Chia văn bản bằng strategy đã chọn.
    3. Embed chunks bằng một provider duy nhất.
    4. Upsert vào ChromaDB với cosine distance.

Mỗi document/chunk phải theo docs/MODULE_CONTRACTS.md. ID cần ổn định để
chạy lại pipeline không tạo dữ liệu trùng. Task 5 phải dùng chung embed_texts().
"""

import os
import re
import time
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"

# 800 ký tự ~ 1 "Điều" ngắn của văn bản luật hoặc 1-2 đoạn bài báo; 500 cắt
# đôi nhiều điều luật. Overlap 15% để câu bị cắt ở biên vẫn có ở chunk kế.
CHUNK_SIZE = 800
CHUNK_OVERLAP = 120
CHUNKING_METHOD = "recursive"
MIN_CHUNK_CHARS = 50  # bỏ mảnh vụn (tiêu đề menu, dòng số trang)

EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "gemini").strip()
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001").strip()
EMBEDDING_DIM = 3072  # gemini-embedding-001 mặc định
EMBED_BATCH_SIZE = 100  # giới hạn số text/request của Gemini

COLLECTION_NAME = "rag_documents"

# Tên file legal không mô tả nội dung -> title hiển thị cho citation.
LEGAL_TITLES = {
    "09.signed": "Luật Du lịch số 09/2017/QH14",
    "DaNang": "QĐ UBND TP Đà Nẵng về thủ tục hành chính lĩnh vực Du lịch (2026)",
    "QDPQ-68-2024": "QĐ UBND TP Hà Nội về mô hình quản lý khu du lịch cấp thành phố (2024)",
}


@lru_cache(maxsize=1)
def _gemini_client():
    from google import genai
    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])


@lru_cache(maxsize=1)
def _sentence_transformer():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBEDDING_MODEL)


def _embed_gemini_batch(batch: list[str]) -> list[list[float]]:
    for attempt in range(5):
        try:
            response = _gemini_client().models.embed_content(
                model=EMBEDDING_MODEL, contents=batch
            )
            return [item.values for item in response.embeddings]
        except Exception as error:
            if "PerDay" in str(error):
                raise RuntimeError(
                    "Hết quota embedding Gemini trong ngày (free tier 1000 lượt). "
                    "Chờ reset hoặc đổi EMBEDDING_PROVIDER/API key."
                ) from error
            # Giới hạn theo phút: chờ rồi thử lại thay vì bỏ cả lần index.
            if "429" not in str(error) or attempt == 4:
                raise
            time.sleep(15 * (attempt + 1))


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed theo EMBEDDING_PROVIDER; Task 5 dùng chung hàm này cho query."""
    if EMBEDDING_PROVIDER == "sentence_transformers":
        return _sentence_transformer().encode(texts).tolist()
    if EMBEDDING_PROVIDER != "gemini":
        raise ValueError(f"Unsupported EMBEDDING_PROVIDER: {EMBEDDING_PROVIDER}")
    vectors = []
    for start in range(0, len(texts), EMBED_BATCH_SIZE):
        vectors.extend(_embed_gemini_batch(texts[start:start + EMBED_BATCH_SIZE]))
    return vectors


def get_collection():
    """Mở Chroma collection dùng cosine distance."""
    import chromadb
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def clean_markdown(text: str) -> str:
    """Bỏ ảnh, giữ chữ của link, bỏ dòng chỉ còn ký hiệu -> chunk ít rác điều hướng."""
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)          # ![alt](img)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)      # [text](url) -> text
    lines = [line.rstrip() for line in text.splitlines()]
    lines = [line for line in lines if re.search(r"\w{2,}", line) or not line.strip()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def _parse_news_header(text: str) -> tuple[str | None, str | None]:
    title = re.search(r"^# (.+)$", text, re.M)
    url = re.search(r"^\*\*Source:\*\* (\S+)", text, re.M)
    return (title.group(1).strip() if title else None, url.group(1) if url else None)


def load_documents() -> list[dict]:
    """Đọc Markdown và trả về danh sách Document."""
    documents = []
    for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        raw = path.read_text(encoding="utf-8")
        doc_type = "legal" if "legal" in path.parts else "news"
        if doc_type == "news":
            title, url = _parse_news_header(raw)
        else:
            title, url = LEGAL_TITLES.get(path.stem), None
        content = clean_markdown(raw)
        if not content:
            continue
        documents.append({
            "id": path.relative_to(STANDARDIZED_DIR).as_posix(),
            "content": content,
            "metadata": {
                "source": path.name,
                "title": title or path.stem,
                "doc_type": doc_type,
                "url": url,
            },
        })
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Chia Document thành chunks có id và chunk_index."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = []
    for document in documents:
        texts = [t for t in splitter.split_text(document["content"]) if len(t.strip()) >= MIN_CHUNK_CHARS]
        for index, text in enumerate(texts):
            chunks.append({
                "id": f"{document['id']}::chunk-{index}",
                "content": text,
                "metadata": {**document["metadata"], "chunk_index": index},
            })
    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Thêm embedding vào từng chunk (không sửa list đầu vào).

    Chunk đã có trong Chroma với nội dung y hệt thì dùng lại vector cũ: chạy lại
    pipeline không tốn quota embedding (free tier Gemini chỉ 1000 lượt/ngày).
    """
    existing = get_collection().get(
        ids=[chunk["id"] for chunk in chunks], include=["documents", "embeddings"]
    )
    cached = {
        item_id: list(vector)
        for item_id, document, vector in zip(existing["ids"], existing["documents"], existing["embeddings"])
    }
    cached_content = dict(zip(existing["ids"], existing["documents"]))
    todo = [c for c in chunks if cached_content.get(c["id"]) != c["content"]]
    print(f"Embedding {len(todo)} new/changed chunks, reusing {len(chunks) - len(todo)}")
    fresh = dict(zip([c["id"] for c in todo], embed_texts([c["content"] for c in todo]))) if todo else {}
    return [{**chunk, "embedding": fresh.get(chunk["id"]) or cached[chunk["id"]]} for chunk in chunks]


def _chroma_metadata(metadata: dict) -> dict:
    # Chroma không nhận None trong metadata.
    return {key: ("" if value is None else value) for key, value in metadata.items()}


def index_to_vectorstore(chunks: list[dict]) -> None:
    """Upsert chunks vào ChromaDB và xoá chunk cũ không còn trong corpus."""
    collection = get_collection()
    new_ids = {chunk["id"] for chunk in chunks}
    stale = [item for item in collection.get(include=[])["ids"] if item not in new_ids]
    if stale:
        collection.delete(ids=stale)
    for start in range(0, len(chunks), 500):
        batch = chunks[start:start + 500]
        collection.upsert(
            ids=[chunk["id"] for chunk in batch],
            documents=[chunk["content"] for chunk in batch],
            embeddings=[chunk["embedding"] for chunk in batch],
            metadatas=[_chroma_metadata(chunk["metadata"]) for chunk in batch],
        )


def run_pipeline() -> None:
    """Chạy load, chunk, embed và index."""
    documents = load_documents()
    chunks = chunk_documents(documents)
    embedded_chunks = embed_chunks(chunks)
    index_to_vectorstore(embedded_chunks)
    print(f"Indexed {len(embedded_chunks)} chunks from {len(documents)} documents")


if __name__ == "__main__":
    run_pipeline()
