#!/usr/bin/env python3
"""
Poll Server - A basic FastAPI application for creating and managing polls
"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)