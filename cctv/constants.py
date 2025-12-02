"""Shared constants for the cctv weather CLI."""

LOGGER_NAME = "cctv_weather"

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

REQUEST_TIMEOUT_SECONDS = 10
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 1
RETRY_BACKOFF_MAX_SECONDS = 3

MODEL_ID = "gpt-4o-mini"
SYSTEM_PROMPT = "You are a concise weather and clothing assistant."
SUMMARY_TEMPLATE = (
    "Summarize today's weather for {display}. "
    "Use this observation data: {observation}. "
    "Give a short headline, current temp in Celsius, wind, and a quick clothing tip."
)

LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d %(message)s"
