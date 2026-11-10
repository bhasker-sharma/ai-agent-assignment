from datetime import date

from fastapi import APIRouter

from server.review.engine import ReviewEngine
from server.review.schemas import Case, ReviewResult


class ApiRoutes:
    """All API endpoints live in this class."""

    def __init__(self) -> None:
        # Loaded once at startup, so a missing index or API key fails fast.
        self.engine = ReviewEngine()
        self.router = APIRouter()
        self.router.add_api_route("/health", self.health, methods=["GET"])
        self.router.add_api_route("/review", self.review, methods=["POST"], response_model=ReviewResult)

    def health(self) -> dict[str, str]:
        return {"status": "ok"}

    def review(self, case: Case) -> ReviewResult:
        """Reviews one case. Send as_of_date in the body to fix 'today'; otherwise the server date is used."""
        # A plain def, so FastAPI runs the slow model call in a worker thread.
        return self.engine.review(case, case.as_of_date or date.today())
