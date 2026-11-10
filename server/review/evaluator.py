from statistics import mean

from server.config import settings
from server.review.engine import ReviewEngine
from server.review.schemas import CaseFile


class Evaluator:
    """Runs the cases that have expected answers and measures how often the engine agrees."""

    def __init__(self, engine: ReviewEngine) -> None:
        self.engine = engine

    def run(self, case_file: CaseFile, runs: int) -> dict:
        """Reviews each case `runs` times, since the model can answer differently on repeat."""
        cases = []
        for case in case_file.cases:
            expected = (case.model_extra or {}).get("expected")
            if not expected:
                continue
            attempts = []
            for _ in range(runs):
                result = self.engine.review(case, case_file.as_of_date)
                cited = [citation.section for citation in result.citations]
                attempts.append(
                    {
                        "decision": result.decision,
                        "rdr_type": result.rdr_type,
                        "sections": cited,
                        "confidence": result.confidence,
                        "reason": result.reason,
                        "decision_ok": result.decision == expected["decision"],
                        "rdr_type_ok": result.rdr_type == expected["rdr_type"],
                        # Share of the expected sections that were cited, and of the cited ones that were expected.
                        "section_recall": len(set(expected["sections"]) & set(cited)) / len(expected["sections"]),
                        "section_precision": len(set(expected["sections"]) & set(cited)) / len(cited) if cited else 0.0,
                    }
                )
            cases.append(
                {
                    "case_id": case.case_id,
                    "expected": expected,
                    "stable": len({(a["decision"], a["rdr_type"]) for a in attempts}) == 1,
                    "attempts": attempts,
                }
            )

        attempts = [attempt for case in cases for attempt in case["attempts"]]
        if not attempts:
            raise ValueError("No case in this file has an 'expected' answer to compare with.")
        correct = [a for a in attempts if a["decision_ok"] and a["rdr_type_ok"]]
        wrong = [a for a in attempts if not (a["decision_ok"] and a["rdr_type_ok"])]
        confusion: dict[str, dict[str, int]] = {}
        for case in cases:
            row = confusion.setdefault(case["expected"]["decision"], {})
            for attempt in case["attempts"]:
                row[attempt["decision"]] = row.get(attempt["decision"], 0) + 1

        return {
            "model": f"{settings.llm_provider}/{settings.llm_model}",
            "as_of_date": str(case_file.as_of_date),
            "runs_per_case": runs,
            "summary": {
                "cases": len(cases),
                "reviews": len(attempts),
                "decision_accuracy": mean(a["decision_ok"] for a in attempts),
                "rdr_type_accuracy": mean(a["rdr_type_ok"] for a in attempts),
                "exact_accuracy": len(correct) / len(attempts),
                "section_recall": mean(a["section_recall"] for a in attempts),
                "section_precision": mean(a["section_precision"] for a in attempts),
                "stable_cases": sum(case["stable"] for case in cases),
                "mean_confidence_correct": mean(a["confidence"] for a in correct) if correct else None,
                "mean_confidence_wrong": mean(a["confidence"] for a in wrong) if wrong else None,
                "confusion": confusion,
            },
            "cases": cases,
        }
