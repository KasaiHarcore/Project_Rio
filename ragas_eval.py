import asyncio
import os
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

# The backend config loader defaults ENABLE_DB_AUTOCREATE to True.
# For evaluation runs we don't require a live Postgres DB, so disable it early
# (before importing backend modules that may initialize AppConfig).
os.environ.setdefault("ENABLE_DB_AUTOCREATE", "False")

import pandas as pd
from datasets import Dataset
from ragas import evaluate
from ragas.metrics.collections.answer_relevancy import AnswerRelevancy
from ragas.metrics.collections.context_precision import ContextPrecision
from ragas.metrics.collections.context_recall import ContextRecall
from ragas.metrics.collections.faithfulness import Faithfulness


def _find_repo_root(start: Path) -> Path:
    """Find repo root by looking for the backend startup module."""
    start = start.resolve()
    candidates = [start, *start.parents]
    for p in candidates:
        # Check for the startup module in the src layout.
        if (p / "src" / "core" / "startup.py").exists():
            return p
    # Fallback: current working directory
    return Path.cwd().resolve()


REPO_ROOT = _find_repo_root(Path(__file__).parent)
SRC_DIR = REPO_ROOT / "src"

# Ensure `backend.*` imports work no matter where the script is run from.
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


from core.startup import run_startup_tasks  # noqa: E402
from core.settings import AgentConfig, get_vectordb_config  # noqa: E402
from infrastructure.integrations.llm import form  # noqa: E402
from utils.log import log_info, log_success, log_warning  # noqa: E402
from application.workflows.graph import build_workflow_graph  # noqa: E402
from application.workflows.state import create_initial_state, extract_answer_from_state  # noqa: E402

def _resolve_val_dataset_path() -> Path:
    """Resolve `val_dataset.csv` from common locations.

    Per your note, we also check the *parent* of the repo root.
    """
    explicit = os.getenv("VAL_DATASET_PATH")
    if explicit:
        p = Path(explicit).expanduser().resolve()
        if p.exists():
            return p

    candidates = [
        REPO_ROOT / "val_dataset.csv",
        REPO_ROOT.parent / "val_dataset.csv",
        Path.cwd().resolve() / "val_dataset.csv",
    ]
    for p in candidates:
        if p.exists():
            return p

    raise FileNotFoundError(
        "Could not find val_dataset.csv. Tried: " + ", ".join(str(p) for p in candidates)
    )


def _safe_text(x: object) -> str:
    if x is None:
        return ""
    if isinstance(x, float) and pd.isna(x):
        return ""
    return str(x)


def _truncate_contexts(contexts: Sequence[str], *, max_chars: int) -> List[str]:
    """Keep contexts list but cap total character budget to avoid LLM overflows."""
    if max_chars <= 0:
        return list(contexts)
    kept: List[str] = []
    total = 0
    for c in contexts:
        if not c:
            continue
        remaining = max_chars - total
        if remaining <= 0:
            break
        if len(c) > remaining:
            kept.append(c[:remaining])
            total = max_chars
            break
        kept.append(c)
        total += len(c)
    return kept


def _contexts_from_retrieval_raw_results(raw_results: str) -> List[str]:
    """Parse contexts from RetrievalService formatted results.

    Expected format per block:
        ### Result 1\n\n*Source:* ...\n\n<page_content>
    Blocks separated by: \n\n---\n\n
    """
    if not raw_results:
        return []

    contexts: List[str] = []
    for block in str(raw_results).split("\n\n---\n\n"):
        b = block.strip()
        if not b:
            continue
        parts = b.split("\n\n", 2)
        if len(parts) == 3:
            context = parts[2]
        elif len(parts) == 2:
            context = parts[1]
        else:
            context = b
        context = context.strip()
        if context:
            contexts.append(context)
    return contexts


def _extract_contexts_from_worker_results(
    worker_results: Sequence[dict], *, max_context_chars: int
) -> List[str]:
    """Extract a list of context strings from workflow worker_results.

    Prefer the retrieval worker's `metadata.raw_results` because it maps cleanly to
    KB chunks; fallback to worker `content` when needed.
    """
    contexts: List[str] = []

    for r in worker_results or []:
        if not isinstance(r, dict):
            continue
        if (r.get("worker_type") or "").lower() != "retrieval":
            continue
        meta = r.get("metadata") or {}
        raw = meta.get("raw_results")
        if raw:
            contexts.extend(_contexts_from_retrieval_raw_results(_safe_text(raw)))
        elif r.get("content"):
            contexts.append(_safe_text(r.get("content")))

    # If retrieval worker didn't run (e.g., mode=chat), include any successful worker content.
    if not contexts:
        for r in worker_results or []:
            if not isinstance(r, dict):
                continue
            if r.get("success") and r.get("content"):
                contexts.append(_safe_text(r.get("content")))

    contexts = [c for c in contexts if c.strip()]
    return _truncate_contexts(contexts, max_chars=max_context_chars)


async def generate_response(question: str, *, config: AgentConfig, max_context_chars: int) -> Tuple[str, List[str]]:
    """Run the backend workflow (same as API) and return (answer, contexts)."""
    # Ensure model selection matches API behavior.
    if config.model_name:
        form.set_model(config.model_name)
    if form.SELECTED_MODEL is None:
        raise RuntimeError(
            "No model selected. Set RAGAS_MODEL_NAME (or configure backend model selection)."
        )
    if getattr(form.SELECTED_MODEL, "llm", None) is None:
        form.SELECTED_MODEL.setup()

    # Run the same supervisor/worker graph, but without Postgres checkpointing.
    # This keeps the evaluation runnable in environments without a DB.
    graph = build_workflow_graph(config=config, checkpointer=None)
    initial_state = create_initial_state(
        question=question,
        thread_id="eval",
        mode=config.mode,
        user_id=None,
        history=None,
        max_iterations=int(os.getenv("RAGAS_MAX_ITERATIONS", "10")),
        metadata={"run_id": "eval"},
    )

    final_state = await asyncio.to_thread(graph.invoke, initial_state)

    answer = _safe_text(extract_answer_from_state(final_state))
    worker_results = final_state.get("worker_results") or []
    contexts = _extract_contexts_from_worker_results(worker_results, max_context_chars=max_context_chars)
    return answer, contexts


def _maybe_build_ragas_embeddings():
    """Try to provide embeddings to RAGAS to avoid defaulting to OpenAI embeddings."""
    try:
        from langchain_huggingface import HuggingFaceEmbeddings

        cfg = get_vectordb_config()
        device = os.getenv("EMBEDDING_DEVICE")
        model_kwargs = {"device": device} if device else {}
        return HuggingFaceEmbeddings(model_name=cfg.embedding_model, model_kwargs=model_kwargs)
    except Exception as e:
        log_warning(f"Could not initialize HuggingFaceEmbeddings for RAGAS: {e}")
        return None


async def main() -> None:
    print("Starting RAGAS evaluation...")

    # Make relative paths stable.
    os.chdir(str(REPO_ROOT))
    
    # 0. Run backend startup (secrets, model registry, vector DB, cache)
    run_startup_tasks()
    log_success("Backend startup completed")

    # 1. Load Dataset
    dataset_path = _resolve_val_dataset_path()
    df = pd.read_csv(dataset_path)
    print(f"Loaded dataset with {len(df)} examples.")

    required_cols = {"question", "ground_truth"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Dataset is missing required columns: {sorted(missing)}")
    
    # 2. Initialize Agent Config (reuse backend workflow)
    k = int(os.getenv("RAGAS_TOP_K", "5"))
    agent_mode = os.getenv("RAGAS_AGENT_MODE", "rag").strip().lower() or "rag"
    if agent_mode not in {"rag", "web", "chat", "sql"}:
        raise ValueError("RAGAS_AGENT_MODE must be one of: rag, web, chat, sql")
    cfg = AgentConfig(mode=agent_mode, top_k=k)

    # Select model (reusing backend registry) and initialize it once.
    model_name = (os.getenv("RAGAS_MODEL_NAME") or os.getenv("MODEL_NAME") or "").strip() or None
    if model_name:
        cfg.model_name = model_name
        form.set_model(model_name)
    if form.SELECTED_MODEL is None:
        # Best-effort default: first registered model.
        names = getattr(form, "get_all_model_names", lambda: [])()
        if not names:
            raise RuntimeError("No models registered. Check backend startup/model registry.")
        form.set_model(names[0])
    if getattr(form.SELECTED_MODEL, "llm", None) is None:
        form.SELECTED_MODEL.setup()
    
    # 3. Generate Answers and Contexts
    questions = [_safe_text(x) for x in df["question"].tolist()]
    ground_truths = [_safe_text(x) for x in df["ground_truth"].tolist()]
    
    answers = []
    contexts_list = []
    
    print("Generating answers and retrieving contexts...")
    max_context_chars = int(os.getenv("RAGAS_MAX_CONTEXT_CHARS", "12000"))
    for i, question in enumerate(questions):
        print(f"Processing {i+1}/{len(questions)}: {question}")
        try:
            answer, contexts = await generate_response(
                question, config=cfg, max_context_chars=max_context_chars
            )
            answers.append(answer)
            contexts_list.append(contexts)
        except Exception as e:
            print(f"Error processing question '{question}': {e}")
            answers.append("Error generating answer.")
            contexts_list.append([])

    # 4. Prepare RAGAS Dataset
    # RAGAS versions differ slightly on expected ground-truth column naming.
    # Provide both to be robust.
    ragas_data = {
        "question": questions,
        "answer": answers,
        "contexts": contexts_list,
        "ground_truth": ground_truths,
        "ground_truths": [[gt] for gt in ground_truths],
    }
    dataset = Dataset.from_dict(ragas_data)
    
    # 5. Run Evaluation
    print("Running RAGAS evaluation metrics...")
    # Make sure the selected model is ready, and pass it into RAGAS so it doesn't
    # default to a different provider.
    if getattr(form.SELECTED_MODEL, "llm", None) is None:
        form.SELECTED_MODEL.setup()
    ragas_llm = form.SELECTED_MODEL.llm
    ragas_embeddings = _maybe_build_ragas_embeddings()

    eval_kwargs = {
        "dataset": dataset,
        "metrics": [Faithfulness(), AnswerRelevancy(), ContextPrecision(), ContextRecall()],
        "llm": ragas_llm,
    }
    if ragas_embeddings is not None:
        eval_kwargs["embeddings"] = ragas_embeddings

    results = evaluate(**eval_kwargs)
    
    print("Evaluation complete!")
    print(results)
    
    # 6. Save Results
    results_df = results.to_pandas()
    out_path = Path(os.getenv("RAGAS_RESULTS_PATH", str(REPO_ROOT / "ragas_results.csv"))).resolve()
    results_df.to_csv(out_path, index=False)
    print(f"Results saved to {out_path}")

if __name__ == "__main__":
    asyncio.run(main())
