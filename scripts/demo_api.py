"""
Live FastAPI Demonstration Script.
Hits /health, /screen, and /results to verify the API server functionality.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from fastapi.testclient import TestClient
from src.api import app
import json

client = TestClient(app)

print("=" * 60)
print("1. Testing GET /health Endpoint")
print("=" * 60)
health = client.get("/health").json()
print(json.dumps(health, indent=2))

print("\n" + "=" * 60)
print("2. Testing POST /screen (Running Screening Batch Pipeline)")
print("=" * 60)
response = client.post("/screen", json={"input_dir": "./resumes", "max_concurrency": 5})
data = response.json()
print("Batch Summary:")
print(json.dumps(data["summary"], indent=2))

print("\n" + "=" * 60)
print("3. Testing GET /results (Fetching Latest Shortlist)")
print("=" * 60)
get_results = client.get("/results").json()
print(f"Total Eligible Ranked: {len(get_results['ranked_candidates'])}")
print(f"Total Ineligible Rejected: {len(get_results['rejected_candidates'])}")
print("\nTop 5 Shortlisted Candidates:")
for c in get_results["ranked_candidates"][:5]:
    b = c["score_breakdown"]
    print(f"Rank {c['rank']}: {c['candidate_name']:<18} | Score: {c['total_score']}/100 | AI: {b['ai_project_depth']}/40 | Py: {b['python_backend']}/30 | Cloud: {b['cloud_fullstack']}/15 | GH: {b['github']}/10 | Eng: {b['engineering_depth']}/5")
    print(f"  Summary: {c['project_summary']}")
    print(f"  Strengths: {', '.join(c['strengths'][:2])}")
