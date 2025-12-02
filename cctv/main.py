"""CLI to forecast weather and provide dressing tips for a given city/country."""
from __future__ import annotations

import argparse
import json
import logging
import uuid
from typing import Any

import requests
from openai import APIConnectionError, APIError, APITimeoutError, OpenAI, RateLimitError
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_random

from cctv.constants import (
    FORECAST_URL,
    GEOCODE_URL,
    LOG_FORMAT,
    LOG_LEVEL,
    LOGGER_NAME,
    MAX_RETRIES,
    MODEL_ID,
    REQUEST_TIMEOUT_SECONDS,
    RETRY_BACKOFF_MAX_SECONDS,
    RETRY_BACKOFF_SECONDS,
    SUMMARY_TEMPLATE,
    SYSTEM_PROMPT,
)
from cctv.env_loader import load_env

logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
log = logging.getLogger(LOGGER_NAME)


def _is_retriable_requests(exc: Exception) -> bool:
    if isinstance(exc, requests.HTTPError):
        status = exc.response.status_code if exc.response else None
        return status is None or status == 429 or 500 <= status < 600
    return isinstance(exc, requests.RequestException)


def _is_retriable_openai(exc: Exception) -> bool:
    if isinstance(exc, (APITimeoutError, APIConnectionError, RateLimitError)):
        return True
    if isinstance(exc, APIError):
        status = getattr(exc, "status_code", None)
        return status is None or status == 429 or 500 <= status < 600
    return False


@retry(
    retry=retry_if_exception(_is_retriable_requests),
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_random(min=RETRY_BACKOFF_SECONDS, max=RETRY_BACKOFF_MAX_SECONDS),
    reraise=True,
)
def get_with_retry(url: str, *, params: dict[str, Any]) -> requests.Response:
    headers = {"X-Client-Request-Id": str(uuid.uuid4())}
    resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS, headers=headers)
    resp.raise_for_status()
    return resp


@retry(
    retry=retry_if_exception(_is_retriable_openai),
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_random(min=RETRY_BACKOFF_SECONDS, max=RETRY_BACKOFF_MAX_SECONDS),
    reraise=True,
)
def create_chat_with_retry(client: OpenAI, *, model: str, messages: list[dict]) -> Any:
    headers = {"X-Client-Request-Id": str(uuid.uuid4())}
    raw = client.chat.completions.with_raw_response.create(
        model=model, messages=messages, extra_headers=headers
    )
    _log_headers("OpenAI response headers", getattr(raw, "headers", None))
    return raw.parse()


def _log_headers(label: str, headers: Any) -> None:
    if not headers:
        return
    try:
        for k, v in dict(headers).items():
            log.info(f"{label} {k} : {v}")
        
    except Exception:
        header_str = str(headers)
        log.info("%s: %s", label, header_str)


def geocode(city: str) -> tuple[float, float, str]:
    resp = get_with_retry(GEOCODE_URL, params={"name": city, "count": 1})
    _log_headers("Geocode response headers", getattr(resp, "headers", None))
    data = resp.json()
    results = data.get("results") or []
    if not results:
        raise SystemExit(f"No location found for '{city}'.")
    try:
        match = results[0]
        display = ", ".join(
            part for part in [match.get("name"), match.get("admin1"), match.get("country")] if part
        )
        return float(match["latitude"]), float(match["longitude"]), display
    except (KeyError, IndexError, ValueError, TypeError) as exc:
        log.error("Error parsing geocoding response for city %s: %s", city, exc)
        raise SystemExit(f"Failed to parse geocoding response for '{city}'.")


def fetch_weather(lat: float, lon: float) -> dict:
    resp = get_with_retry(
        FORECAST_URL,
        params={"latitude": lat, "longitude": lon, "current_weather": True, "timezone": "auto"},
    )
    _log_headers("Forecast response headers", getattr(resp, "headers", None))
    data = resp.json()
    if "current_weather" not in data:
        raise SystemExit("Weather data missing from response.")
    return data["current_weather"]


def extract_text(response) -> str:
    if not response:
        return ""

    choices = getattr(response, "choices", None) or []
    if not choices:
        return ""

    try:
        message = choices[0].message
        content = message.content
    except (AttributeError, IndexError, TypeError):
        return ""

    if isinstance(content, list):
        chunks = [part.text for part in content if getattr(part, "type", "") == "text"]
        return "".join(chunks).strip()
    if isinstance(content, str):
        return content.strip()
    return ""


def run(city: str) -> str:
    load_env()
    client = OpenAI()
    lat, lon, display = geocode(city)
    current = fetch_weather(lat, lon)

    prompt = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": SUMMARY_TEMPLATE.format(display=display, observation=json.dumps(current)),
        },
    ]

    response = create_chat_with_retry(client, model=MODEL_ID, messages=prompt)
    message = extract_text(response)
    return message or "No response text returned."


def main():
    parser = argparse.ArgumentParser(
        description="Get a concise weather forecast and dressing tip for a city/country."
    )
    parser.add_argument("location", help='Location string, e.g., "Beijing, China".')
    args = parser.parse_args()

    output = run(args.location)
    print(output)


if __name__ == "__main__":
    main()
