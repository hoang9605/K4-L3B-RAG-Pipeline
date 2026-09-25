import re

import streamlit as st
from dotenv import load_dotenv

from src.task10_generation import generate_with_citation


load_dotenv()

st.set_page_config(
    page_title="Hỏi đáp Du lịch Hội An",
    page_icon="🏮",
    layout="wide",
)

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.title("🏮 Du lịch Hội An")
    st.caption(
        "Chatbot RAG trả lời từ Luật Du lịch 2017, quy định du lịch Đà Nẵng/Hà Nội "
        "và các bài viết về vé tham quan, ẩm thực, lễ hội Hội An."
    )
    top_k = st.slider("Số chunks", 3, 10, 5)
    if st.button("Xoá hội thoại"):
        st.session_state.messages = []
        st.rerun()


def render_sources(answer: str, sources: list[dict]) -> None:
    """Hiện nguồn; nguồn được cite [n] trong câu trả lời được đánh dấu và mở sẵn."""
    if not sources:
        return
    cited = {int(n) for n in re.findall(r"\[(\d+)\]", answer)}
    st.caption(f"Nguồn ({len(cited)}/{len(sources)} được trích dẫn)")
    for index, source in enumerate(sources, 1):
        metadata = source["metadata"]
        mark = "✅" if index in cited else "▫️"
        label = (
            f"{mark} [{index}] {metadata['title']} · {source['retrieval_method']} "
            f"· score {source['score']:.4f}"
        )
        with st.expander(label, expanded=index in cited):
            if metadata.get("url"):
                st.markdown(f"🔗 [{metadata['url']}]({metadata['url']})")
            st.caption(f"{metadata['source']} · chunk {metadata['chunk_index']} · {metadata['doc_type']}")
            st.text(source["content"])


st.title("Hỏi đáp Du lịch Hội An")
st.caption("Ví dụ: Giá vé tham quan phố cổ Hội An? · Khu du lịch là gì? · Trung thu Hội An có gì?")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        render_sources(message["content"], message.get("sources", []))

query = st.chat_input("Nhập câu hỏi...")

if query:
    st.session_state.messages.append({"role": "user", "content": query})

    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Đang tìm nguồn và trả lời..."):
            result = generate_with_citation(query, top_k)
        answer, sources = result["answer"], result["sources"]
        st.markdown(answer)
        render_sources(answer, sources)

    st.session_state.messages.append(
        {"role": "assistant", "content": answer, "sources": sources}
    )
