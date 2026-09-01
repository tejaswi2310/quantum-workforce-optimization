from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from app.core.exceptions import CustomException
from app.models.database import engine
from app.models.models import Base

# Create DB tables
Base.metadata.create_all(bind=engine)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Quantum Workforce Optimizer API",
    description="""API for the Quantum Workforce Optimizer platform.
    
**Authentication Note:** 
JWT Access Tokens obtained via `/api/v1/auth/login` are valid for **15 minutes**. 
After 15 minutes, requests to protected endpoints will return `401 Unauthorized`. 
When using this Swagger UI, you must re-authenticate using the **Authorize** button if your token expires.
""",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins in development, restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routers import auth, projects, datasets, forecast, optimize, validate, reports, dashboard
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(datasets.router)
app.include_router(forecast.router)
app.include_router(optimize.router)
app.include_router(validate.router)
app.include_router(reports.router)
app.include_router(dashboard.router)

# Global exception handler
@app.exception_handler(CustomException)
async def custom_exception_handler(request: Request, exc: CustomException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": exc.message, "detail": exc.detail}
    )

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/ready")
async def ready_check():
    return {"status": "ready"}
