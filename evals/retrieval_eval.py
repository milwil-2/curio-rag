import json
from datetime import datetime
from pathlib import Path

from curio.retrieval import store, embed, rerank


FIXTURES = [
    {
        "question": "Who is considered the father of thermodynamics and what did he publish in 1824?",
        "expected_id": "Thermodynamics::2",
    },
    {
        "question": "What does the zeroth law of thermodynamics state?",
        "expected_id": "Thermodynamics::5",
    },
    {
        "question": "Why is the zeroth law called 'zeroth' rather than another number?",
        "expected_id": "Thermodynamics::6",
    },
    {
        "question": "Who invented matrix mechanics?",
        "expected_id": "Quantum mechanics::9",
    },
    {
        "question": "What did Louis de Broglie propose about particles in 1923?",
        "expected_id": "Quantum mechanics::25",
    },
    {
        "question": "What is the many-worlds interpretation of quantum mechanics?",
        "expected_id": "Interpretations of quantum mechanics::2",
    },
    {
        "question": "What is a qubit?",
        "expected_id": "Measurement in quantum mechanics::6",
    },
    {
        "question": "What does wave function collapse mean?",
        "expected_id": "Introduction to quantum mechanics::6",
    },
    {
        "question": "What is the Bohr model and what discovery preceded it?",
        "expected_id": "History of quantum mechanics::5",
    },
    {
        "question": "What is the predicted heat death of the universe?",
        "expected_id": "Entropy::32",
    },
    {
        "question": "Who is the Born rule named after?",
        "expected_id": "Quantum mechanics::1",
    },
    {
        "question": "What is the Copenhagen interpretation of quantum mechanics?",
        "expected_id": "Quantum mechanics::22",
    },
    {
        "question": "What is quantum entanglement?",
        "expected_id": "Quantum mechanics::2",
    },
    {
        "question": "What is the Schrodinger equation used for?",
        "expected_id": "Quantum mechanics::4",
    },
    {
        "question": "What did Einstein's 1905 paper on the photoelectric effect demonstrate?",
        "expected_id": "Quantum mechanics::24",
    },
]


MAX_K = 5
RERANK_CANDIDATES = 10


def naive_dense(question: str) -> list[str]:
    query_vector = embed.embed_query(question)
    results = store.search_table(query_vector, k=MAX_K)
    return [r["id"] for r in results]


def hybrid(question: str) -> list[str]:
    results = store.hybrid_search(question, k=MAX_K)
    return [r["id"] for r in results]


def hybrid_rerank(question: str) -> list[str]:
    candidates = store.hybrid_search(question, k=RERANK_CANDIDATES)
    results = rerank.rerank(question, candidates, k=MAX_K)
    return [r["id"] for r in results]


def recall_at_k(ranked_ids_per_fixture: list[list[str]], expected_ids: list[str], k: int) -> float:
    hits = sum(1 for ids, expected in zip(ranked_ids_per_fixture, expected_ids) if expected in ids[:k])
    return hits / len(expected_ids)


def write_results_json(
    results_per_strategy: dict[str, list[list[str]]],
    expected_ids: list[str],
    path: Path,
) -> None:
    """Write structured recall@k results so the web app can render the eval banner."""
    strategy_names = list(results_per_strategy.keys())
    ks = [1, 3, 5]

    recall_at_k_map: dict[str, dict[str, float]] = {}
    multipliers_map: dict[str, dict[str, float | None]] = {}

    baseline = "Naive dense"

    for k in ks:
        per_strategy = {
            name: round(recall_at_k(results_per_strategy[name], expected_ids, k), 3)
            for name in strategy_names
        }
        recall_at_k_map[str(k)] = per_strategy

        baseline_score = per_strategy.get(baseline, 0.0)
        mult_for_k: dict[str, float | None] = {}
        for name in strategy_names:
            if name == baseline:
                continue
            if baseline_score == 0:
                mult_for_k[name] = None
            else:
                mult_for_k[name] = round(per_strategy[name] / baseline_score, 3)
        multipliers_map[str(k)] = mult_for_k

    payload = {
        "fixtures_count": len(expected_ids),
        "strategies": strategy_names,
        "recall_at_k": recall_at_k_map,
        "multipliers_vs_naive": multipliers_map,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }

    path.write_text(json.dumps(payload, indent=2) + "\n")


def main() -> None:
    strategies = [
        ("Naive dense", naive_dense),
        ("Hybrid (RRF)", hybrid),
        ("Hybrid + rerank", hybrid_rerank),
    ]

    print(f"Evaluating {len(FIXTURES)} fixtures\n")

    expected_ids = [f["expected_id"] for f in FIXTURES]
    results_per_strategy: dict[str, list[list[str]]] = {}

    for name, fn in strategies:
        print(f"Running {name}...")
        results_per_strategy[name] = [fn(f["question"]) for f in FIXTURES]

    print()
    for k in [1, 3, 5]:
        print(f"Recall@{k}")
        print("-" * 40)
        for name, _ in strategies:
            score = recall_at_k(results_per_strategy[name], expected_ids, k)
            print(f"  {name:20s} {score:.1%}")
        print()

    results_path = Path(__file__).parent / "results.json"
    write_results_json(results_per_strategy, expected_ids, results_path)
    print(f"Wrote evals/results.json")


if __name__ == "__main__":
    main()
