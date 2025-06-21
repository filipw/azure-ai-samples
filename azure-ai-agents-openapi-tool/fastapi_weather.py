import datetime
import random
from typing import List, Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Weather Forecast API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class WeatherForecast(BaseModel):
    date: str  # ISO format date
    temperatureC: int
    summary: Optional[str] = None
    
    @property
    def temperatureF(self) -> int:
        return 32 + int(self.temperatureC / 0.5556)

summaries = [
    "Freezing", "Bracing", "Chilly", "Cool", "Mild", 
    "Warm", "Balmy", "Hot", "Sweltering", "Scorching"
]

@app.get("/weatherforecast", response_model=List[WeatherForecast], operation_id="GetWeatherForecast")
async def get_weather_forecast():
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
