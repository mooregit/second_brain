from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import ask, decisions, github, gitlab, gmail, graph, ideas, items, memories, processing_runs, projects, questions, settings, tasks

app = FastAPI(title="Second Brain Inbox", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(items.router)
app.include_router(memories.router)
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(ideas.router)
app.include_router(decisions.router)
app.include_router(questions.router)
app.include_router(ask.router)
app.include_router(graph.router)
app.include_router(processing_runs.router)
app.include_router(settings.router)
app.include_router(gmail.router)
app.include_router(gitlab.router)
app.include_router(github.router)
