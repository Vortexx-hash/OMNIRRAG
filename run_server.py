"""Entry point — starts the RAG Pipeline API server with uvicorn."""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["api", "pipeline", "models"],
    )
