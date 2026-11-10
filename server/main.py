from fastapi import FastAPI

from server.api.routes import ApiRoutes


class Application:
    def __init__(self) -> None:
        self.api = FastAPI(title="DMS AI System")
        self.api.include_router(ApiRoutes().router)


app = Application().api
