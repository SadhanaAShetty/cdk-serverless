from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.db import init_db
from app.config import settings
from app.services.storage import image_storage
from pathlib import Path
import uvicorn
import boto3

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
    """Setup database and services"""
    init_db()
    reports_folder = Path(settings.REPORTS_DIR)
    reports_folder.mkdir(parents=True, exist_ok=True)
    
    #Initialize image storage service with config
    if settings.S3_BUCKET_NAME:
        image_storage.bucket_name = settings.S3_BUCKET_NAME
        image_storage.region = settings.AWS_REGION
        
        
        
        if settings.AWS_PROFILE:
            session = boto3.Session(profile_name=settings.AWS_PROFILE)
            image_storage.s3_client = session.client('s3', region_name=settings.AWS_REGION)
            print(f"Using AWS Profile: {settings.AWS_PROFILE}")
        else:
            image_storage.s3_client = boto3.client('s3', region_name=settings.AWS_REGION)
    
    print("Server is running")
    print(f" Database: {settings.DATABASE_URL}")
    print(f" Reports directory: {settings.REPORTS_DIR}")
    if settings.S3_BUCKET_NAME:
        print(f" S3 Bucket: {settings.S3_BUCKET_NAME}")
        print(f" AWS Region: {settings.AWS_REGION}")


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