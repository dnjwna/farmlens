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