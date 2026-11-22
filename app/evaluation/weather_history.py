"""
Weather context for a photo's capture date (production uses "the last 7 days from now").

Source order:
1. Open-Meteo forecast API with start_date/end_date: same source as production, covers recent months.
2. Open-Meteo archive API (ERA5 reanalysis): older dates. Coarser grid than (1), so the source
   is recorded per sample and reported.
Both are model data, not ground stations.
"""
from datetime import date, timedelta
from typing import Optional

import httpx

from app.services.weather_service import OPEN_METEO_URL, summarize_recent_weather

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
DAILY_VARS = ["precipitation_sum", "relative_humidity_2m_mean", "temperature_2m_max", "temperature_2m_min"]


def window_for(taken: date, days: int = 7) -> tuple[date, date]:
    """The `days` full days before the photo; the capture day itself is excluded, as in production."""
    return taken - timedelta(days=days), taken - timedelta(days=1)


def _complete(daily: dict) -> bool:
    values = [v for key in DAILY_VARS for v in daily.get(key, [])]
    return bool(values) and all(v is not None for v in values)


async def weather_context_for_date(
    client: httpx.AsyncClient, lat: float, lon: float, taken: date, days: int = 7
) -> tuple[Optional[str], Optional[str]]:
    """Returns (context sentence, source) or (None, None) if no complete data was found."""
    start, end = window_for(taken, days)
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": DAILY_VARS,
        "timezone": "Asia/Jakarta",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
    }
    for source, url in (("forecast", OPEN_METEO_URL), ("archive", ARCHIVE_URL)):
        try:
            response = await client.get(url, params=params)
            if response.status_code >= 400:
                continue  # e.g. date outside this API's range
            daily = response.json().get("daily", {})
        except (httpx.HTTPError, ValueError):
            continue
        if _complete(daily):
            context = summarize_recent_weather({k: v for k, v in daily.items() if k != "time"})
            if context:
                return context, source
    return None, None
