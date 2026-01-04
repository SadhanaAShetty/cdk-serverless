from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.db import init_db
from app.config import settings
from pathlib import Path
import uvicorn

app = FastAPI()

# Include API routes
app.include_router(router, prefix="/api/v1")

#Allow all CORS 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    """Setup database"""
    init_db()
    reports_folder = Path(settings.REPORTS_DIR)
    reports_folder.mkdir(parents=True, exist_ok=True)
    print("Server is running")
    print(f" Database: {settings.DATABASE_URL}")
    print(f" Reports directory: {settings.REPORTS_DIR}")


@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "HOLIDAY HOME SWAP API",
        "version": "1.0.0",
        "docs": "/docs"
    }



#For local run
if __name__ =="__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)