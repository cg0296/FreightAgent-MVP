import json
import os
from anthropic import Anthropic
from typing import Optional
from app.models import ParsedQuoteData
from app.config import settings


def get_client():
    """Get Anthropic client, preferring environment variable over config"""
    api_key = os.getenv("ANTHROPIC_API_KEY") or settings.ANTHROPIC_API_KEY
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in environment or config")
    return Anthropic(api_key=api_key)


PARSE_PROMPT = """You are an expert at parsing freight quote request emails. Extract the following information from the email and return it as valid JSON.

CRITICAL: You MUST respond with ONLY a JSON object. Do not include markdown, backticks, or any text before or after the JSON.

Required fields:
- origin_city: string (city name)
- origin_state: string (2-letter state code, e.g., "IL", "CA")
- destination_city: string (city name)
- destination_state: string (2-letter state code)
- equipment_type: string (e.g., "53' dry van", "flatbed", "reefer")
- quantity: number (quantity of trucks or loads)

Optional fields:
- driver_type: string or null (e.g., "team", "solo", "owner-op")
- loading_date_start: string or null (YYYY-MM-DD format)
- loading_date_end: string or null (YYYY-MM-DD format)
- delivery_date: string or null (YYYY-MM-DD format)
- special_requirements: array of strings (e.g., ["$250k insurance", "e-track required"])
- confidence: number between 0 and 1 (your confidence in this parse)
- notes: string (any clarifications or missing info)

JSON Response Format:
{{"origin_city": "...", "origin_state": "...", "destination_city": "...", "destination_state": "...", "equipment_type": "...", "quantity": 0, "driver_type": null, "loading_date_start": null, "loading_date_end": null, "delivery_date": null, "special_requirements": [], "confidence": 0.95, "notes": ""}}

Email to parse:
{email_text}

Your response should be ONLY the JSON object with no additional text."""


def parse_email(email_text: str, client_name: Optional[str] = None) -> ParsedQuoteData:
    """
    Parse a freight quote request email using Claude API.

    Args:
        email_text: The raw email content
        client_name: Optional client name from context

    Returns:
        ParsedQuoteData with extracted information

    Raises:
        ValueError: If parsing fails or JSON is invalid
    """

    prompt = PARSE_PROMPT.format(email_text=email_text)

    client = get_client()

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
    except Exception as api_error:
        raise ValueError(f"Claude API call failed: {str(api_error)}")

    # Extract the response text
    response_text = message.content[0].text.strip()

    # Remove markdown code blocks if present
    if "```" in response_text:
        # Extract JSON between backticks
        start = response_text.find("{")
        end = response_text.rfind("}") + 1
        if start != -1 and end > start:
            response_text = response_text[start:end]

    response_text = response_text.strip()
    # Parse JSON
    try:
        parsed_data = json.loads(response_text)
    except json.JSONDecodeError as e:
        # Try to extract JSON object more aggressively
        try:
            # Find first { and last }
            start = response_text.find("{")
            end = response_text.rfind("}") + 1

            if start >= 0 and end > start:
                json_str = response_text[start:end]
                parsed_data = json.loads(json_str)
            else:
                raise ValueError(f"No JSON object found in response: {repr(response_text[:200])}")
        except json.JSONDecodeError as inner_e:
            raise ValueError(f"Failed to parse Claude's response as JSON: {inner_e}\nResponse: {repr(response_text[:200])}")

    # Validate required fields
    required_fields = [
        "origin_city", "origin_state", "destination_city", "destination_state",
        "equipment_type", "quantity"
    ]

    missing = [f for f in required_fields if f not in parsed_data or parsed_data[f] is None]
    if missing:
        raise ValueError(f"Missing required fields: {missing}")

    # Convert to ParsedQuoteData model (validates types)
    return ParsedQuoteData(**parsed_data)


def improve_parse_with_user_feedback(
    original_parse: ParsedQuoteData,
    user_edits: dict,
    original_email: str
) -> ParsedQuoteData:
    """
    Re-parse email with user feedback to improve accuracy.

    Args:
        original_parse: The original parsed data
        user_edits: Fields the user corrected
        original_email: The original email text

    Returns:
        Updated ParsedQuoteData
    """

    # Convert original to dict and apply edits
    parse_dict = original_parse.model_dump()
    parse_dict.update(user_edits)

    # Return updated model
    return ParsedQuoteData(**parse_dict)
