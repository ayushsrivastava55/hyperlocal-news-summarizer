#!/usr/bin/env python3
"""
Benchmark summarization models on live news samples (or proxy references).

Default models:
 - facebook/bart-large-cnn
 - sshleifer/distilbart-cnn-12-6

Metrics:
 - load_time_sec (per model)
 - avg_in_chars, avg_out_chars, avg_compression (out/in)
 - avg_latency_sec_per_sample, total_time_sec
 - throughput_samples_per_min

ROUGE:
 - If `evaluate` and `rouge_score` are installed, computes ROUGE-1/2/L/Lsum.
 - Reference by default is the RSS description (proxy). You can change with --reference.
"""

import sys
from pathlib import Path
# Ensure project root is on sys.path when running as "python scripts/benchmark_summarizers.py"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
import json
import time
from typing import List, Dict, Tuple, Optional

import torch
from transformers import pipeline

from feed_collector import FeedCollector, NAGPUR_FEED_CONFIGS


def collect_samples(limit_per_feed: int = 2, max_total: int = 6, reference: str = "desc") -> List[Dict[str, str]]:
    collector = FeedCollector()
    raw = collector.collect_multiple_feeds(NAGPUR_FEED_CONFIGS, per_feed_limit=limit_per_feed)
    samples: List[Dict[str, str]] = []

    for a in raw:
        title = a.get("title") or ""
        desc = a.get("description") or ""
        input_text = (title + " " + desc).strip()

        if not input_text:
            continue

        if reference == "desc":
            ref_text = desc.strip()
        elif reference == "input":
            ref_text = input_text  # self-ROUGE proxy (not a true eval)
        else:
            ref_text = ""

        samples.append({"input": input_text, "reference": ref_text})

        # Stop if we've collected enough
        if len(samples) >= (max_total or 6):
            break

    # fallback dummy if nothing
    if not samples:
        samples = [
            {
                "input": "The city council announced new measures to improve waste management, including door-to-door collection and segregation drives, aiming to reduce landfill burden and increase recycling rates across neighborhoods.",
                "reference": "",
            },
            {
                "input": "Local authorities inaugurated a new public health center equipped with telemedicine facilities and emergency services to enhance healthcare access for rural populations surrounding the city.",
                "reference": "",
            },
        ]
    return samples


def benchmark_model(model_name: str, samples: List[Dict[str, str]], max_length: int = 100, min_length: int = 30) -> Dict:
    device = 0 if torch.cuda.is_available() else -1
    t0 = time.time()
    summarizer = pipeline(
        "summarization",
        model=model_name,
        tokenizer=model_name,
        device=device
    )
    load_time = time.time() - t0

    in_chars: List[int] = []
    out_chars: List[int] = []
    latencies: List[float] = []
    preds: List[str] = []
    refs: List[str] = []

    t_start = time.time()
    for sample in samples:
        text = sample["input"]
        ref = sample.get("reference", "")
        in_chars.append(len(text))
        s0 = time.time()
        out = summarizer(
            text,
            max_length=max_length,
            min_length=min_length,
            do_sample=False
        )
        latencies.append(time.time() - s0)
        summary_text = out[0]["summary_text"] if out and isinstance(out, list) else ""
        out_chars.append(len(summary_text))
        preds.append(summary_text)
        if ref:
            refs.append(ref)
    total_time = time.time() - t_start

    n = len(samples)
    avg_in = sum(in_chars) / n
    avg_out = sum(out_chars) / n
    avg_compression = avg_out / avg_in if avg_in > 0 else 0.0
    avg_latency = sum(latencies) / n
    throughput = (n / total_time * 60.0) if total_time > 0 else 0.0

    result = {
        "model": model_name,
        "device": "cuda" if device == 0 else "cpu",
        "num_samples": n,
        "load_time_sec": round(load_time, 3),
        "avg_in_chars": round(avg_in, 1),
        "avg_out_chars": round(avg_out, 1),
        "avg_compression": round(avg_compression, 3),
        "avg_latency_sec_per_sample": round(avg_latency, 3),
        "total_time_sec": round(total_time, 3),
        "throughput_samples_per_min": round(throughput, 2),
    }

    # Optional ROUGE
    try:
        import evaluate  # type: ignore
        if refs:
            rouge = evaluate.load("rouge")
            rouge_scores = rouge.compute(predictions=preds[:len(refs)], references=refs)
            # keep key metrics
            result["rouge"] = {
                "rouge1": round(rouge_scores.get("rouge1", 0.0), 4),
                "rouge2": round(rouge_scores.get("rouge2", 0.0), 4),
                "rougeL": round(rouge_scores.get("rougeL", 0.0), 4),
                "rougeLsum": round(rouge_scores.get("rougeLsum", 0.0), 4),
                "reference": "rss_description",
                "count": len(refs),
            }
        else:
            result["rouge"] = {"note": "no references available; provide --reference desc|input"}
    except Exception:
        pass

    return result


def main():
    parser = argparse.ArgumentParser(description="Benchmark summarization models on live news samples.")
    parser.add_argument(
        "--models",
        type=str,
        default="facebook/bart-large-cnn,sshleifer/distilbart-cnn-12-6",
        help="Comma-separated model names"
    )
    parser.add_argument("--limit_per_feed", type=int, default=2)
    parser.add_argument("--max_total", type=int, default=6)
    parser.add_argument("--max_length", type=int, default=100)
    parser.add_argument("--min_length", type=int, default=30)
    parser.add_argument("--output", type=str, default="")
    parser.add_argument("--reference", type=str, default="desc", choices=["desc", "input", "none"],
                        help="Reference for ROUGE: 'desc' (RSS description), 'input' (self-ROUGE proxy), or 'none'")
    args = parser.parse_args()

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    print(f"Collecting samples (limit_per_feed={args.limit_per_feed}, max_total={args.max_total}, reference={args.reference})...")
    samples = collect_samples(limit_per_feed=args.limit_per_feed, max_total=args.max_total, reference=args.reference)
    print(f"Collected {len(samples)} samples")

    all_results: List[Dict] = []
    for m in models:
        print(f"\nBenchmarking {m} ...")
        res = benchmark_model(m, samples, max_length=args.max_length, min_length=args.min_length)
        all_results.append(res)
        print(json.dumps(res, indent=2))

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2)
        print(f"\nSaved results to {args.output}")


if __name__ == "__main__":
    main()


