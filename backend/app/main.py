import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load env variables from backend/.env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

from app.routers import data

app = FastAPI(
    title="Water Quality Monitoring Dashboard API",
    description="FastAPI Backend for real-time monitoring and predictions of water quality at KMITL.",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to S3/CloudFront domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(data.router)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "Water Quality Monitoring API",
        "message": "Water Quality Monitoring API is running successfully."
    }

