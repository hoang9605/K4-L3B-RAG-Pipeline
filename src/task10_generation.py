"""
Task 10 — Generation có citation.

Hướng dẫn:
    1. Retrieve top-k chunks.
    2. Reorder để giảm lost-in-the-middle.
    3. Format context kèm title và source.
    4. Gọi provider được chọn trong .env.
    5. Trả answer, sources và retrieval_source.

Nếu context không đủ hoặc provider lỗi, trả safe refusal; không bịa thông tin.
"""

import os

from dotenv import load_dotenv

from .task9_retrieval_pipeline import retrieve


load_dotenv()

TOP_K = 5
TOP_P = 0.9
TEMPERATURE = 0.3
# False -> dense-only (Config A của A/B evaluation); signature hàm giữ theo contract.
USE_RERANKING = True

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").strip()
LLM_MODEL = os.getenv("LLM_MODEL", "").strip()
DEFAULT_MODELS = {
    "gemini": "gemini-3.5-flash",
    "openai": "gpt-5-mini",
    "anthropic": "claude-sonnet-5",
}

REFUSAL = "Tôi không thể xác minh thông tin này từ nguồn hiện có."

SYSTEM_PROMPT = f"""Bạn là trợ lý du lịch Việt Nam (tập trung Hội An) và quy định pháp luật về du lịch.
Quy tắc bắt buộc:
- Chỉ trả lời dựa trên các Document trong context. Không dùng kiến thức bên ngoài.
- Sau mỗi câu/ý có thông tin từ context, ghi citation dạng [n] với n là số Document, ví dụ [1] hoặc [1][3].
- Chỉ cite số Document có trong context.
- Nếu context không chứa thông tin để trả lời, trả lời đúng một câu: "{REFUSAL}"
- Context có thể bằng tiếng Anh; luôn trả lời bằng tiếng Việt, giữ nguyên con số, tên riêng."""


def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """Đưa chunks quan trọng về đầu và cuối context (không sửa list gốc)."""
    if len(chunks) <= 2:
        return list(chunks)
    front = chunks[::2]
    back = chunks[1::2]
    return front + back[::-1]


def format_context(chunks: list[dict]) -> str:
    """Tạo context có title và source label.

    Số Document lấy từ field "citation" (thứ hạng gốc) nếu có, để [n] trong
    câu trả lời trỏ đúng sources[n-1] kể cả sau khi reorder.
    """
    parts = []
    for index, chunk in enumerate(chunks, 1):
        metadata = chunk["metadata"]
        number = chunk.get("citation", index)
        parts.append(
            f"[Document {number} | Title: {metadata['title']} | "
            f"Source: {metadata['source']}]\n{chunk['content']}"
        )
    return "\n\n---\n\n".join(parts)


def call_llm(system_prompt: str, user_message: str) -> str:
    """Gọi OpenAI, Gemini hoặc Anthropic theo cấu hình."""
    model = LLM_MODEL or DEFAULT_MODELS.get(LLM_PROVIDER, "")
    if LLM_PROVIDER == "gemini":
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        response = client.models.generate_content(
            model=model,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=TEMPERATURE,
                top_p=TOP_P,
            ),
        )
        return response.text or ""
    if LLM_PROVIDER == "openai":
        from openai import OpenAI
        response = OpenAI(api_key=os.environ["OPENAI_API_KEY"]).chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=TEMPERATURE,
            top_p=TOP_P,
        )
        return response.choices[0].message.content or ""
    if LLM_PROVIDER == "anthropic":
        from anthropic import Anthropic
        response = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"]).messages.create(
            model=model,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            temperature=TEMPERATURE,
        )
        return "".join(block.text for block in response.content if block.type == "text")
    raise ValueError(f"Unsupported LLM_PROVIDER: {LLM_PROVIDER}")


def _refusal() -> dict:
    return {"answer": REFUSAL, "sources": [], "retrieval_source": "none"}


def generate_with_citation(query: str, top_k: int = TOP_K) -> dict:
    """Trả về GenerationResult."""
    try:
        chunks = retrieve(query, top_k=top_k, use_reranking=USE_RERANKING)
    except Exception as error:
        print(f"Retrieval failed: {error}")
        return _refusal()
    if not chunks:
        return _refusal()

    numbered = [{**chunk, "citation": index} for index, chunk in enumerate(chunks, 1)]
    context = format_context(reorder_for_llm(numbered))
    user_message = f"Context:\n{context}\n\nQuestion: {query}"
    try:
        answer = call_llm(SYSTEM_PROMPT, user_message).strip()
    except Exception as error:
        print(f"LLM call failed: {error}")
        return _refusal()
    # Cả câu trả lời chỉ là câu từ chối -> không kèm sources.
    if not answer or answer.rstrip(".") == REFUSAL.rstrip("."):
        return _refusal()
    return {
        "answer": answer,
        "sources": chunks,  # sort theo score; [n] trong answer = sources[n-1]
        "retrieval_source": "pageindex" if chunks[0]["retrieval_method"] == "pageindex" else "hybrid",
    }


if __name__ == "__main__":
    for q in ["Khu du lịch là gì?", "Giá vé tham quan phố cổ Hội An?", "Công thức nấu phở bò?"]:
        result = generate_with_citation(q)
        print(f"\nQ: {q}\n[{result['retrieval_source']}] {result['answer']}")
        for index, source in enumerate(result["sources"], 1):
            print(f"  [{index}] {source['metadata']['title']} ({source['id']})")
