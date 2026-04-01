from fastapi import FastAPI, HTTPException, staticfiles, Depends, Header
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import secrets
import hashlib
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.config import settings
from app.db import CarrierRecord, QuoteRecord, get_db, init_database, serialize_parsed_data
from app.models import (
    EmailParseRequest,
    EmailParseResponse,
    ParsedQuoteData,
    QuoteGenerationRequest,
    QuoteGenerationResponse,
    Carrier,
    CarrierCreate,
    LoginRequest,
    LoginResponse,
    QuoteSummary,
)
from app.agents.email_parser import parse_email
from app.excel_generator import generate_quote_sheet

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Serve static files (frontend)
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", staticfiles.StaticFiles(directory=static_dir), name="static")

# Serve downloads directory
os.makedirs("downloads", exist_ok=True)
app.mount("/downloads", staticfiles.StaticFiles(directory="downloads"), name="downloads")

# In-memory user sessions and credentials
valid_tokens: dict[str, dict] = {}  # token -> {username, expires_at}

# Default users for MVP (username -> hashed_password)
USERS = {
    "ADMIN": hashlib.sha256("fuzzysheep".encode()).hexdigest(),
    "Beltmann": hashlib.sha256("Beltmann".encode()).hexdigest(),
}

# Auth helpers
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def verify_token(token: str) -> str:
    """Returns username if token is valid, raises HTTPException if not"""
    if token not in valid_tokens:
        raise HTTPException(status_code=401, detail="Invalid token")

    session = valid_tokens[token]
    if session["expires_at"] < datetime.now():
        del valid_tokens[token]
        raise HTTPException(status_code=401, detail="Token expired")

    return session["username"]


@app.on_event("startup")
async def startup_event():
    init_database()


# Health check
@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME}


# Login endpoint
@app.post("/api/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Authenticate user and return session token"""
    if request.username not in USERS:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(request.password, USERS[request.username]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Generate token valid for 7 days
    token = generate_token()
    valid_tokens[token] = {
        "username": request.username,
        "expires_at": datetime.now() + timedelta(days=7)
    }

    return LoginResponse(
        success=True,
        token=token,
        username=request.username
    )


# Dependency for protected endpoints
async def get_current_user(authorization: Optional[str] = Header(None)) -> str:
    """Extract token from Authorization header and verify"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing token")

    parts = authorization.split()
    if len(parts) != 2 or parts[0] != "Bearer":
        raise HTTPException(status_code=401, detail="Invalid token format")

    token = parts[1]
    return verify_token(token)


# Email parsing endpoint
@app.post("/api/parse-email", response_model=EmailParseResponse)
async def parse_email_endpoint(request: EmailParseRequest, username: str = Depends(get_current_user)):
    """
    Parse a client email to extract quote details.

    Returns structured data ready for quote sheet generation.
    """
    try:
        parsed_data = parse_email(request.email_text, request.client_name)
        return EmailParseResponse(success=True, data=parsed_data)
    except ValueError as e:
        return EmailParseResponse(success=False, error=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing email: {str(e)}")


# Quote generation endpoint
@app.post("/api/generate-quote-sheet", response_model=QuoteGenerationResponse)
async def generate_quote_sheet_endpoint(
    request: QuoteGenerationRequest,
    username: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate an Excel quote sheet from parsed data and carriers.
    """
    try:
        file_path, filename = generate_quote_sheet(
            quote_data=request.quote_data,
            carriers=request.carriers,
            client_name=request.client_name or "Quote"
        )

        file_url = f"/downloads/{filename}"

        quote_record = QuoteRecord(
            client_name=request.client_name,
            parsed_data_json=serialize_parsed_data(request.quote_data.model_dump(mode="json")),
            filename=filename,
            file_url=file_url,
        )
        db.add(quote_record)
        db.commit()

        return QuoteGenerationResponse(
            success=True,
            file_url=file_url,
            filename=filename
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating quote sheet: {str(e)}")


# Download quote sheet
@app.get("/api/downloads/{filename}")
async def download_quote(filename: str):
    """Download a generated quote sheet."""
    file_path = os.path.join("downloads", filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        file_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename
    )


# Carrier management endpoints
@app.get("/api/carriers", response_model=List[Carrier])
async def get_carriers(username: str = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get all carriers."""
    carriers = db.scalars(select(CarrierRecord).order_by(CarrierRecord.name)).all()
    return [
        Carrier(
            id=carrier.id,
            name=carrier.name,
            email=carrier.email,
            phone=carrier.phone,
            created_at=carrier.created_at,
        )
        for carrier in carriers
    ]


@app.post("/api/carriers", response_model=Carrier)
async def create_carrier(
    carrier: CarrierCreate,
    username: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a new carrier."""
    new_carrier = CarrierRecord(
        name=carrier.name,
        email=carrier.email,
        phone=carrier.phone
    )
    db.add(new_carrier)
    db.commit()
    db.refresh(new_carrier)
    return Carrier.model_validate(new_carrier)


@app.delete("/api/carriers/{carrier_id}")
async def delete_carrier(
    carrier_id: int,
    username: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a carrier."""
    carrier = db.get(CarrierRecord, carrier_id)
    if carrier is None:
        raise HTTPException(status_code=404, detail="Carrier not found")

    db.delete(carrier)
    db.commit()
    return {"status": "deleted"}


@app.get("/api/quotes", response_model=List[QuoteSummary])
async def get_quotes(username: str = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get recently generated quotes."""
    quotes = db.scalars(select(QuoteRecord).order_by(QuoteRecord.created_at.desc())).all()
    return [
        QuoteSummary(
            id=quote.id,
            client_name=quote.client_name,
            filename=quote.filename,
            file_url=quote.file_url,
            created_at=quote.created_at,
        )
        for quote in quotes
    ]


# Root endpoint
@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT
    )
