from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime, date


# Authentication
class LoginRequest(BaseModel):
    """Login request with username and password"""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response with token"""
    success: bool
    token: Optional[str] = None
    username: Optional[str] = None
    error: Optional[str] = None


# Email Parsing
class ParsedQuoteData(BaseModel):
    """Parsed quote data from client email"""
    origin_city: str
    origin_state: str
    destination_city: str
    destination_state: str
    equipment_type: str
    driver_type: Optional[str] = None
    quantity: int
    loading_date_start: Optional[date] = None
    loading_date_end: Optional[date] = None
    delivery_date: Optional[date] = None
    special_requirements: List[str] = []
    confidence: float  # 0-1, how confident Claude is in the parse
    notes: Optional[str] = None


class EmailParseRequest(BaseModel):
    """Request to parse a client email"""
    email_text: str
    client_name: Optional[str] = None


class EmailParseResponse(BaseModel):
    """Response from email parsing"""
    success: bool
    data: Optional[ParsedQuoteData] = None
    error: Optional[str] = None


# Carrier Management
class CarrierBase(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None


class CarrierCreate(CarrierBase):
    pass


class CarrierUpdate(CarrierBase):
    pass


class Carrier(CarrierBase):
    id: int
    created_at: datetime = Field(default_factory=lambda: datetime.now())

    class Config:
        from_attributes = True


# Quote Generation
class QuoteGenerationRequest(BaseModel):
    """Request to generate quote sheet"""
    quote_data: ParsedQuoteData
    carriers: List[Carrier]
    client_name: Optional[str] = None


class QuoteGenerationResponse(BaseModel):
    """Response from quote generation"""
    success: bool
    file_url: Optional[str] = None
    filename: Optional[str] = None
    error: Optional[str] = None


# Quote Record
class QuoteBase(BaseModel):
    client_name: Optional[str]
    parsed_data: ParsedQuoteData


class QuoteCreate(QuoteBase):
    pass


class Quote(QuoteBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class QuoteSummary(BaseModel):
    id: int
    client_name: Optional[str] = None
    filename: Optional[str] = None
    file_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
