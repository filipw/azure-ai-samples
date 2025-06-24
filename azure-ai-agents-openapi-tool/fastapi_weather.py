import datetime
import os
import random
from typing import List
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

load_dotenv()

tunnel_url = os.environ.get("DEV_TUNNEL_URL")
if not tunnel_url:
    print("⚠️  Error: DEV_TUNNEL_URL environment variable is not set")
    exit(1)
else:
    print(f"🔗 Using tunnel URL: {tunnel_url}")
    
app = FastAPI(
    title="Weather Forecast API",
    description="A simple weather forecast API that provides 5-day weather predictions with temperature and weather conditions",
    version="1.0.0",
    openapi_url="/openapi.json",
    servers=[
        {
            "url": tunnel_url,
            "description": "API server"
        }
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class WeatherForecast(BaseModel):
    """
    Weather forecast data model containing temperature and weather conditions for a specific date.
    """
    date: str = Field(..., description="The date of the forecast in ISO format (YYYY-MM-DD)", example="2025-06-23")
    temperatureC: int = Field(..., description="Temperature in Celsius degrees", example=25, ge=-50, le=60)
    summary: str = Field(..., description="Brief description of weather conditions", example="Warm")
    
    @property
    def temperatureF(self) -> int:
        """Convert Celsius temperature to Fahrenheit"""
        return 32 + int(self.temperatureC / 0.5556)

summaries = [
    "Freezing", "Bracing", "Chilly", "Cool", "Mild", 
    "Warm", "Balmy", "Hot", "Sweltering", "Scorching"
]

@app.get(
    "/weatherforecast", 
    response_model=List[WeatherForecast], 
    operation_id="GetWeatherForecast",
    summary="Get 5-day weather forecast",
    description="Retrieves a 5-day weather forecast starting from today. Each forecast includes the date, temperature in Celsius (and Fahrenheit), and a summary of weather conditions.",
    response_description="A list of weather forecasts for the next 5 days",
    tags=["Weather"]
)
async def get_weather_forecast():
    """
    Get a 5-day weather forecast starting from today.
    
    This endpoint generates random weather data for demonstration purposes.
    Each forecast includes:
    - Date in ISO format (YYYY-MM-DD)
    - Temperature in Celsius (automatically converted to Fahrenheit)
    - Weather summary description
    
    Returns:
        List[WeatherForecast]: A list of 5 weather forecasts starting from today
    """
    forecasts = []
    for index in range(0, 5):
        current_date = datetime.datetime.now() + datetime.timedelta(days=index)
        forecast = WeatherForecast(
            date=current_date.strftime("%Y-%m-%d"),
            temperatureC=random.randint(-20, 55),
            summary=random.choice(summaries)
        )
        forecasts.append(forecast)
    
    return forecasts

if __name__ == "__main__":
    uvicorn.run("fastapi_weather:app", host="127.0.0.1", port=5270, reload=True)
