# src/scripts/eval.py
import subprocess
import sys

# We use subprocess to run each evaluation in isolation.
# This ensures the environment variable is picked up cleanly on import,
# and prevents state pollution between runs.

EVAL_CODE = """
import os
import time
import logging

# Suppress verbose logging
logging.basicConfig(level=logging.WARNING)

from src.core.retrieval import init_retrieval
from src.core import retrieval

GOLDEN_DATASET = [
    {"query": "Rust memory safety", "expected": ["rust", "memory"]},
    {"query": "OpenAI or DeepSeek API", "expected": ["openai", "deepseek", "llm"]},
    {"query": "Linux desktop environment", "expected": ["linux", "desktop", "gnome", "kde"]},
    {"query": "Database performance optimization", "expected": ["database", "postgres", "sqlite", "sql"]},
    {"query": "Building a startup", "expected": ["startup", "founder", "business"]}
]

init_retrieval()

print(f"\\nEvaluating Configuration: {os.getenv('RETRIEVAL_MODE').upper()}")
print("-" * 60)

total_hits = 0
total_mrr = 0
latencies = []

for item in GOLDEN_DATASET:
    start = time.perf_counter()
    hits = retrieval.hybrid_search(item["query"], k=5)
    latency = (time.perf_counter() - start) * 1000
    latencies.append(latency)
    
    rr = 0
    for rank, hit in enumerate(hits, 1):
        # Check if any expected keyword is in title or url
        match = any(
            exp.lower() in (hit.get("title") or "").lower() or 
            exp.lower() in (hit.get("url") or "").lower() 
            for exp in item["expected"]
        )
        if match:
            rr = 1.0 / rank
            break
            
    total_hits += (1 if rr > 0 else 0)
    total_mrr += rr
    print(f"Query: '{item['query']}' | Found: {'Yes' if rr > 0 else 'No'} | RR: {rr:.2f}")

hit_rate = (total_hits / len(GOLDEN_DATASET)) * 100
avg_mrr = total_mrr / len(GOLDEN_DATASET)
avg_lat = sum(latencies) / len(latencies)

print(f"\\nResults:")
print(f"Hit Rate (Recall@5): {hit_rate:.1f}%")
print(f"MRR: {avg_mrr:.3f}")
print(f"Avg Latency: {avg_lat:.1f}ms")
"""

def run_eval(mode):
    print(f"\n" + "="*60)
    print(f"Starting evaluation for mode: {mode.upper()}")
    print("="*60)
    
    # Set environment variable and run the eval code in a fresh process
    import os
    env = os.environ.copy()
    env["RETRIEVAL_MODE"] = mode
    
    result = subprocess.run(
        [sys.executable, "-c", EVAL_CODE],
        env=env,
        capture_output=False, # Let output stream directly to terminal
        text=True
    )
    
    if result.returncode != 0:
        print(f"Error running evaluation for {mode}")

if __name__ == "__main__":
    # Run all three modes
    run_eval("vector")
    run_eval("bm25")
    run_eval("hybrid")
    print("\nEvaluation complete!")