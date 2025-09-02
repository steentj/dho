#!/usr/bin/env python3
"""Stage 5: Compare search results between main and shadow search APIs.

Usage:
  python scripts/compare_search_results.py --queries soegemaskine/shadow_queries.txt \
      --main http://localhost:8080 --shadow http://localhost:18000 \
      --top 5 --output comparison_report.json

Produces JSON report containing per-query overlap metrics.
"""
from __future__ import annotations
import argparse
import json
from dataclasses import dataclass
from typing import List, Dict, Any
import httpx

@dataclass
class QueryResult:
    query: str
    main_ids: List[str]
    shadow_ids: List[str]
    overlap: float
    jaccard: float

async def fetch_results(client: httpx.AsyncClient, base_url: str, query: str, top: int) -> List[Dict[str, Any]]:
    payload = {"query": query}
    r = await client.post(f"{base_url.rstrip('/')}/search", json=payload, timeout=30)
    r.raise_for_status()
    data = r.json()
    # Expect data structure with 'resultater' or similar; fallback to whole JSON if unknown.
    if isinstance(data, dict):
        if 'resultater' in data and isinstance(data['resultater'], list):
            return data['resultater'][:top]
        if 'results' in data and isinstance(data['results'], list):
            return data['results'][:top]
    if isinstance(data, list):  # raw list fallback
        return data[:top]
    return []

async def process_queries(args) -> Dict[str, Any]:
    report: Dict[str, Any] = {"queries": [], "summary": {}}
    async with httpx.AsyncClient() as client:
        all_overlaps = []
        for line in open(args.queries, 'r', encoding='utf-8'):
            q = line.strip()
            if not q or q.startswith('#'):
                continue
            try:
                main_res = await fetch_results(client, args.main, q, args.top)
                shadow_res = await fetch_results(client, args.shadow, q, args.top)
            except Exception as e:
                report["queries"].append({
                    "query": q,
                    "error": str(e)
                })
                continue

            main_ids = [str(r.get('book_id') or r.get('bog_id') or r.get('bookId')) for r in main_res]
            shadow_ids = [str(r.get('book_id') or r.get('bog_id') or r.get('bookId')) for r in shadow_res]
            main_set = set(main_ids)
            shadow_set = set(shadow_ids)
            if main_set or shadow_set:
                overlap_count = len(main_set & shadow_set)
                union_count = len(main_set | shadow_set) or 1
                overlap_ratio = overlap_count / (min(len(main_set), len(shadow_set)) or 1)
                jaccard = overlap_count / union_count
            else:
                overlap_ratio = 0.0
                jaccard = 0.0
            report["queries"].append({
                "query": q,
                "main_ids": main_ids,
                "shadow_ids": shadow_ids,
                "overlap_ratio": round(overlap_ratio, 3),
                "jaccard": round(jaccard, 3)
            })
            all_overlaps.append(jaccard)
        if all_overlaps:
            report["summary"] = {
                "avg_jaccard": round(sum(all_overlaps) / len(all_overlaps), 3),
                "query_count": len(all_overlaps)
            }
    return report

def main():
    parser = argparse.ArgumentParser(description="Compare main vs shadow search results")
    parser.add_argument('--queries', required=True, help='Text file with one query per line')
    parser.add_argument('--main', default='http://localhost:8080', help='Main API base URL')
    parser.add_argument('--shadow', default='http://localhost:18000', help='Shadow API base URL')
    parser.add_argument('--top', type=int, default=5, help='Top N results to consider')
    parser.add_argument('--output', '-o', default='comparison_report.json', help='Output JSON file')
    args = parser.parse_args()
    import asyncio
    report = asyncio.run(process_queries(args))
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Report written to {args.output}")

if __name__ == '__main__':
    main()
