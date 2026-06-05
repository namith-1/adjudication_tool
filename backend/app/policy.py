import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict


def load_json_file(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_policy() -> Dict[str, Any]:
    base = Path(__file__).resolve().parents[2]
    policy_path = base / "Instruction_files" / "policy_terms (1).json"
    return load_json_file(policy_path)


def is_active_policy(policy: Dict[str, Any], treatment_date: date) -> bool:
    effective_date = datetime.fromisoformat(policy["effective_date"]).date()
    return treatment_date >= effective_date
