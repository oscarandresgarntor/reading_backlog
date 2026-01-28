"""FastAPI application for the reading backlog server."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ..config import SERVER_HOST, SERVER_PORT
from .routes import router

# Application setup
app = FastAPI(
    title="Reading Backlog API",
    description="Save articles for later reading with automatic metadata extraction",
    version="0.1.0",
)

# CORS configuration for Chrome extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Chrome extensions have unique origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)

# Templates for dashboard
templates_dir = Path(__file__).parent.parent / "dashboard" / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


@app.get("/", response_class=HTMLResponse)
async def root():
    """Redirect to dashboard."""
    return """
    <html>
        <head><meta http-equiv="refresh" content="0; url=/dashboard" /></head>
        <body><a href="/dashboard">Go to Dashboard</a></body>
    </html>
    """


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Render the web dashboard."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


def run_server():
    """Run the server with uvicorn."""
    import uvicorn
    uvicorn.run(
        "src.server.app:app",
        host=SERVER_HOST,
        port=SERVER_PORT,
        reload=True,
    )


if __name__ == "__main__":
    run_server()
