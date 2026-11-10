import argparse
import json
from pathlib import Path

from server.config import settings
from server.documents.index_builder import IndexBuilder
from server.review.engine import ReviewEngine
from server.review.evaluator import Evaluator
from server.review.schemas import CaseFile


class CommandLine:
    """All terminal commands live in this class."""

    def __init__(self) -> None:
        self.parser = argparse.ArgumentParser(prog="python -m server.cli")
        commands = self.parser.add_subparsers(dest="command", required=True)
        commands.add_parser("index", help="Rebuild the search index from the document folders")

        review = commands.add_parser("review", help="Review every case in a case file")
        review.add_argument("case_file", type=Path)
        review.add_argument("--out", type=Path, default=Path("predictions.json"))

        evaluate = commands.add_parser("eval", help="Review the cases with expected answers and score them")
        evaluate.add_argument("case_file", type=Path, nargs="?", default=Path("data/cases/dev_cases.json"))
        evaluate.add_argument("--runs", type=int, default=1, help="Reviews per case, to measure stability")
        evaluate.add_argument("--out", type=Path, default=Path("eval_results.json"))

    def run(self) -> None:
        arguments = self.parser.parse_args()
        if arguments.command == "index":
            self.index()
        elif arguments.command == "review":
            self.review(arguments.case_file, arguments.out)
        elif arguments.command == "eval":
            self.evaluate(arguments.case_file, arguments.runs, arguments.out)

    def index(self) -> None:
        builder = IndexBuilder(settings.knowledge_dir, settings.evidence_dir, settings.index_dir)
        chunks = builder.build()
        rules = sum(chunk.kind == "rule" for chunk in chunks)
        print(f"Indexed {len(chunks)} chunks: {rules} rule, {len(chunks) - rules} evidence")

    def review(self, case_file: Path, out: Path) -> None:
        cases = CaseFile.model_validate_json(case_file.read_text(encoding="utf-8"))
        engine = ReviewEngine()
        results = []
        for case in cases.cases:
            result = engine.review(case, cases.as_of_date)
            results.append(result.model_dump(mode="json"))
            print(f"{result.case_id}: {result.decision} | {result.rdr_type} | confidence {result.confidence}")
        out.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"Wrote {len(results)} results to {out}")

    def evaluate(self, case_file: Path, runs: int, out: Path) -> None:
        cases = CaseFile.model_validate_json(case_file.read_text(encoding="utf-8"))
        report = Evaluator(ReviewEngine()).run(cases, runs)

        for case in report["cases"]:
            expected = case["expected"]
            print(f"{case['case_id']}  expected {expected['decision']} | {expected['rdr_type']} | {expected['sections']}")
            for attempt in case["attempts"]:
                verdict = "PASS" if attempt["decision_ok"] and attempt["rdr_type_ok"] else "FAIL"
                print(f"   {verdict}  got {attempt['decision']} | {attempt['rdr_type']} | {attempt['sections']} | confidence {attempt['confidence']}")
            if not case["stable"]:
                print("   UNSTABLE: the answer changed between runs")

        summary = report["summary"]
        print(f"\nModel {report['model']}, {summary['cases']} cases x {report['runs_per_case']} runs")
        for name in ("decision_accuracy", "rdr_type_accuracy", "exact_accuracy", "section_recall", "section_precision"):
            print(f"  {name:<20} {summary[name]:.0%}")
        print(f"  {'stable_cases':<20} {summary['stable_cases']}/{summary['cases']}")
        print(f"  {'confidence correct':<20} {summary['mean_confidence_correct']}")
        print(f"  {'confidence wrong':<20} {summary['mean_confidence_wrong']}")
        print(f"  {'confusion':<20} {summary['confusion']}  (expected -> got)")
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Full report written to {out}")


if __name__ == "__main__":
    CommandLine().run()
