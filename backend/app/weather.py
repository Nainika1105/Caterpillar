from __future__ import annotations

import os
from datetime import datetime, timezone

import httpx


class WeatherService:
    def __init__(self) -> None:
        self.api_url = os.getenv("WEATHER_API_URL", "https://api.openweathermap.org/data/2.5/weather")
        self.api_key = os.getenv("WEATHER_API_KEY")

    async def fetch(self, latitude: float, longitude: float) -> dict[str, object]:
        if not self.api_key:
            raise RuntimeError("WEATHER_API_KEY is not configured")
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(self.api_url, params={"lat": latitude, "lon": longitude, "appid": self.api_key, "units": "metric"})
            response.raise_for_status()
            payload = response.json()
        rain = float(payload.get("rain", {}).get("1h", 0))
        alert = None
        weather = payload.get("weather", [{}])
        if weather and weather[0].get("main") in {"Thunderstorm", "Tornado"}:
            alert = "thunderstorm_lightning"
        elif rain >= 15:
            alert = "heavy_rain"
        return {"observed_at": datetime.now(timezone.utc), "temperature_c": float(payload["main"]["temp"]), "rain_mm": rain, "alert": alert}


weather_service = WeatherService()
