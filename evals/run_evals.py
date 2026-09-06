"""Deterministic offline routing, evidence and safety regression gate."""

import json
from pathlib import Path
from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app


def main():
    rows = [
        json.loads(line)
        for line in Path(__file__).with_name("eval_dataset.jsonl").read_text().splitlines()
        if line.strip()
    ]
    passed = 0
    with TestClient(
        create_app(
            Settings(
                _env_file=None,
                llm_provider="mock",
                vector_store="memory",
                auth_mode="none",
                app_env="test",
            )
        )
    ) as client:
        for i, row in enumerate(rows):
            result = client.post("/chat", json={"message": row["input"]}).json()
            ok = (
                result["route"] == row["expected_route"]
                and row["must_contain"].lower() in result["answer"].lower()
                and result["blocked"] == row.get("blocked", False)
                and (
                    not row.get("source")
                    or row["source"] in [c["source"] for c in result["citations"]]
                )
            )
            passed += int(ok)
            print(json.dumps({"case": i, "passed": ok}))
    print(f"Passed {passed}/{len(rows)}")
    return int(passed != len(rows))


if __name__ == "__main__":
    raise SystemExit(main())
