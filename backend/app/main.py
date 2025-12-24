from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.interview import router as interview_router

app = FastAPI(title="Mentoria Backend")

# Allow frontend (React) to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # OK for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

# Mount interview APIs
app.include_router(interview_router, prefix="/api/interviews")
