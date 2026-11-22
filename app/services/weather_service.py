import httpx
from typing import Optional

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Mapping kode cuaca Open-Meteo ke deskripsi Bahasa Indonesia
WEATHER_CODES = {
    0: "Cerah", 1: "Cerah Berawan", 2: "Berawan", 3: "Mendung",
    45: "Berkabut", 48: "Berkabut Tebal",
    51: "Gerimis Ringan", 53: "Gerimis", 55: "Gerimis Lebat",
    61: "Hujan Ringan", 63: "Hujan Sedang", 65: "Hujan Lebat",
    71: "Salju Ringan", 73: "Salju", 75: "Salju Lebat",
    80: "Hujan Lokal Ringan", 81: "Hujan Lokal", 82: "Hujan Lokal Lebat",
    95: "Badai Petir", 96: "Badai Petir + Hujan Es",
}

def get_farming_advice(daily: dict) -> str:
    """Generate rekomendasi pertanian berdasarkan data cuaca."""
    advice = []

    avg_rain = sum(daily["precipitation_sum"]) / len(daily["precipitation_sum"])
    max_temp = max(daily["temperature_2m_max"])
    min_humidity = min(daily["relative_humidity_2m_min"])

    if avg_rain > 10:
        advice.append("Curah hujan tinggi minggu ini — tunda pemupukan dan pastikan drainase lahan berfungsi baik.")
    elif avg_rain < 2:
        advice.append("Curah hujan rendah — tingkatkan frekuensi irigasi, terutama pagi hari.")
    else:
        advice.append("Kondisi curah hujan ideal untuk pertumbuhan tanaman.")

    if max_temp > 35:
        advice.append("Suhu sangat tinggi — hindari pemupukan siang hari, lakukan sebelum jam 9 pagi atau setelah jam 4 sore.")
    elif max_temp < 20:
        advice.append("Suhu rendah — pertumbuhan tanaman melambat, kurangi dosis pupuk nitrogen.")
    else:
        advice.append("Suhu optimal untuk pertumbuhan tanaman.")

    if min_humidity < 40:
        advice.append("Kelembaban rendah — waspadai serangan tungau dan thrips, pertimbangkan pemasangan mulsa.")
    elif min_humidity > 85:
        advice.append("Kelembaban tinggi — tingkatkan kewaspadaan terhadap penyakit jamur seperti blast dan busuk daun.")

    return " ".join(advice)


async def get_weather(latitude: float, longitude: float) -> dict:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": [
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation",
            "weather_code",
            "wind_speed_10m",
        ],
        "daily": [
            "weather_code",
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "relative_humidity_2m_max",
            "relative_humidity_2m_min",
        ],
        "timezone": "Asia/Jakarta",
        "forecast_days": 7,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(OPEN_METEO_URL, params=params)
        response.raise_for_status()
        data = response.json()

    current = data["current"]
    daily = data["daily"]

    # Format forecast 7 hari
    forecast = []
    for i in range(len(daily["time"])):
        forecast.append({
            "date": daily["time"][i],
            "weather": WEATHER_CODES.get(daily["weather_code"][i], "Tidak diketahui"),
            "temp_max": daily["temperature_2m_max"][i],
            "temp_min": daily["temperature_2m_min"][i],
            "rain_mm": daily["precipitation_sum"][i],
            "humidity_max": daily["relative_humidity_2m_max"][i],
            "humidity_min": daily["relative_humidity_2m_min"][i],
        })

    return {
        "current": {
            "temperature": current["temperature_2m"],
            "humidity": current["relative_humidity_2m"],
            "precipitation": current["precipitation"],
            "weather": WEATHER_CODES.get(current["weather_code"], "Tidak diketahui"),
            "wind_speed": current["wind_speed_10m"],
        },
        "forecast_7_days": forecast,
        "farming_advice": get_farming_advice(daily),
    }

# ---------------------------------------------------------------------------
# Recent-weather context for diagnosis
# ---------------------------------------------------------------------------

HUMID_DAY_THRESHOLD = 85  # % mean RH; sustained high humidity favours fungal disease
RAIN_DAY_THRESHOLD = 1.0  # mm; days with at least this much rain count as rainy


def summarize_recent_weather(daily: dict) -> Optional[str]:
    """
    Turn Open-Meteo daily data for past days into one Indonesian sentence.
    Pure function so it can be unit-tested without network access.
    Missing values (None) are skipped; returns None if nothing usable remains.
    """
    def clean(key: str) -> list:
        return [v for v in daily.get(key, []) if v is not None]

    rain = clean("precipitation_sum")
    rh = clean("relative_humidity_2m_mean")
    tmax = clean("temperature_2m_max")
    tmin = clean("temperature_2m_min")
    if not (rain or rh or tmax):
        return None

    parts = []
    if rain:
        rainy = sum(1 for r in rain if r >= RAIN_DAY_THRESHOLD)
        parts.append(
            f"total hujan {sum(rain):.0f} mm ({rainy} dari {len(rain)} hari hujan)"
        )
    if rh:
        humid = sum(1 for h in rh if h >= HUMID_DAY_THRESHOLD)
        parts.append(
            f"kelembapan rata-rata {sum(rh) / len(rh):.0f}% "
            f"({humid} hari dengan kelembapan >= {HUMID_DAY_THRESHOLD}%)"
        )
    if tmax and tmin:
        parts.append(f"suhu {min(tmin):.0f}-{max(tmax):.0f} derajat C")

    n_days = max(len(rain), len(rh), len(tmax))
    return f"{n_days} hari terakhir: " + ", ".join(parts) + "."


async def get_recent_weather_context(
    latitude: float, longitude: float, days: int = 7
) -> Optional[str]:
    """
    Fetch the last `days` days of weather for a location and summarise it.
    Today is excluded because its values are still partly forecast.
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": [
            "precipitation_sum",
            "relative_humidity_2m_mean",
            "temperature_2m_max",
            "temperature_2m_min",
        ],
        "timezone": "Asia/Jakarta",
        "past_days": days,
        "forecast_days": 1,
    }
    async with httpx.AsyncClient(timeout=8.0) as client:
        response = await client.get(OPEN_METEO_URL, params=params)
        response.raise_for_status()
        daily = response.json()["daily"]

    past_only = {key: values[:days] for key, values in daily.items() if key != "time"}
    return summarize_recent_weather(past_only)


async def get_daily_observations(latitude: float, longitude: float, past_days: int) -> list[dict]:
    """
    Daily rain and max temperature for the last `past_days` completed days
    (today excluded because it is still partly forecast), oldest first.
    Source is Open-Meteo's model data for past days, not a ground station.
    """
    past_days = max(1, min(past_days, 92))  # Open-Meteo accepts at most 92 past days
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": ["precipitation_sum", "temperature_2m_max"],
        "timezone": "Asia/Jakarta",
        "past_days": past_days,
        "forecast_days": 1,
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(OPEN_METEO_URL, params=params)
        response.raise_for_status()
        daily = response.json()["daily"]

    rows = [
        {"date": d, "rain_mm": r, "temp_max": t}
        for d, r, t in zip(daily["time"], daily["precipitation_sum"], daily["temperature_2m_max"])
    ]
    return rows[:past_days]
