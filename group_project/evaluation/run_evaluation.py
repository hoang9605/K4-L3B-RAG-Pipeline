"""
A/B evaluation: Config A (dense-only) vs Config B (hybrid + RRF).

Chạy: python -m group_project.evaluation.run_evaluation [--limit N]

Cùng golden dataset, generator, evaluator, prompt, top_k; chỉ đổi retrieval.
Evaluator = Gemini qua endpoint OpenAI-compatible (langchain-openai có sẵn).
Kết quả: results_<config>.csv (từng câu) + summary.json (trung bình, latency).
"""

import argparse
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

import src.task10_generation as generation


load_dotenv()

HERE = Path(__file__).parent
GOLDEN = HERE / "golden_dataset.json"
TOP_K = 5
GEMINI_OPENAI_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
EVALUATOR_MODEL = os.getenv("EVALUATOR_MODEL", "gemini-3.1-flash-lite").strip()
METRIC_COLUMNS = ["faithfulness", "answer_relevancy", "context_recall", "llm_context_precision_with_reference"]
CONFIGS = {"A_dense": False, "B_hybrid_rrf": True}


def run_config(dataset: list[dict], use_reranking: bool) -> tuple[list[dict], float]:
    """Sinh câu trả lời cho mọi câu hỏi với một cấu hình retrieval."""
    generation.USE_RERANKING = use_reranking
    rows, started = [], time.time()
    for item in dataset:
        result = generation.generate_with_citation(item["question"], top_k=TOP_K)
        rows.append({
            "user_input": item["question"],
            "response": result["answer"],
            # Refusal không có source -> context rỗng; ragas cần ít nhất 1 chuỗi.
            "retrieved_contexts": [s["content"] for s in result["sources"]] or [""],
            "reference": item["expected_answer"],
            "reference_contexts": [item["expected_context"]],
            "retrieval_source": result["retrieval_source"],
        })
    return rows, (time.time() - started) / max(len(dataset), 1)


def score(rows: list[dict]):
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    from ragas import EvaluationDataset, RunConfig, evaluate
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import LangchainLLMWrapper
    from ragas.metrics import (
        Faithfulness,
        LLMContextPrecisionWithReference,
        LLMContextRecall,
        ResponseRelevancy,
    )

    key = os.environ["GEMINI_API_KEY"]
    llm = LangchainLLMWrapper(ChatOpenAI(model=EVALUATOR_MODEL, base_url=GEMINI_OPENAI_URL, api_key=key, temperature=0))
    embeddings = LangchainEmbeddingsWrapper(OpenAIEmbeddings(
        model="gemini-embedding-001", base_url=GEMINI_OPENAI_URL, api_key=key,
        check_embedding_ctx_length=False,
    ))
    dataset = EvaluationDataset.from_list(
        [{k: v for k, v in row.items() if k != "retrieval_source"} for row in rows]
    )
    result = evaluate(
        dataset,
        metrics=[Faithfulness(), ResponseRelevancy(strictness=1), LLMContextRecall(), LLMContextPrecisionWithReference()],
        llm=llm,
        embeddings=embeddings,
        # Free tier giới hạn request/phút -> ít worker, retry nhiều.
        run_config=RunConfig(max_workers=2, max_retries=10, max_wait=90, timeout=300),
    )
    return result.to_pandas()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="chỉ chạy N câu đầu (smoke test)")
    parser.add_argument("--configs", nargs="+", default=list(CONFIGS), choices=list(CONFIGS),
                        help="chỉ chạy lại một số config; kết quả config khác giữ trong summary.json")
    args = parser.parse_args()

    dataset = json.loads(GOLDEN.read_text(encoding="utf-8"))[: args.limit]
    summary_file = HERE / "summary.json"
    previous = json.loads(summary_file.read_text(encoding="utf-8")) if summary_file.exists() else {}
    summary = {"evaluator_model": EVALUATOR_MODEL, "generator_model": generation.LLM_MODEL,
               "top_k": TOP_K, "n_questions": len(dataset), "configs": previous.get("configs", {})}
    for name in args.configs:
        use_reranking = CONFIGS[name]
        print(f"\n=== {name}: generating ===")
        rows, latency = run_config(dataset, use_reranking)
        print(f"=== {name}: scoring ===")
        frame = score(rows)
        frame["retrieval_source"] = [row["retrieval_source"] for row in rows]
        frame.to_csv(HERE / f"results_{name}.csv", index=False, encoding="utf-8-sig")
        means = {col: round(float(frame[col].mean()), 4) for col in METRIC_COLUMNS}
        means["average"] = round(sum(means.values()) / len(METRIC_COLUMNS), 4)
        summary["configs"][name] = {"scores": means, "seconds_per_question": round(latency, 2),
                                    "refusals": int((frame["retrieval_source"] == "none").sum())}
        print(json.dumps(summary["configs"][name], indent=2))
    summary_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
