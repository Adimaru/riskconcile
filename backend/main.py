import os # Import os module to access environment variables
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import datetime

app = FastAPI()

# Configure CORS (Cross-Origin Resource Sharing)
app.add_middleware(
    CORSMiddleware,
    # IMPORTANT: Add your future Netlify URL here
    # For local development, keep http://localhost:5173
    # Replace 'https://YOUR-NETLIFY-APP-NAME.netlify.app' with your actual Netlify URL
     allow_origins=[
        "http://localhost:5173",
        "https://wondrous-croissant-826418.netlify.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Twelve Data API Configuration
# Get API key from environment variable (secure for deployment)
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")
if not TWELVE_DATA_API_KEY:
    # For local development, you can fall back to a hardcoded key or raise an error
    # But for Render, ensure this env var is set.
    # For now, let's make it clear it's missing if not set
    print("WARNING: TWELVE_DATA_API_KEY environment variable not set!")
    # Optionally, for local testing without setting env var, you could temporarily do:
    # TWELVE_DATA_API_KEY = "e73ae4ff25e041e58abc2a0212198297" # Your key
    
TWELVE_DATA_BASE_URL = "https://api.twelvedata.com"

# Pydantic models for data validation and response structuring
class HistoricalData(BaseModel):
    date: str
    close: float

class StockData(BaseModel):
    symbol: str
    name: str = "N/A"
    price: float
    change: float
    change_percent: str
    historical_data: list[HistoricalData] = []

@app.get("/")
async def read_root():
    return {"message": "Welcome to the RiskConcile Stock Tracker API"}

@app.get("/api/stock/{ticker}", response_model=StockData)
async def get_stock_data(ticker: str):
    if not TWELVE_DATA_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key not configured on backend server."
        )

    async with httpx.AsyncClient() as client:
        # --- 1. Fetch Current Quote Data ---
        quote_params = {
            "symbol": ticker,
            "apikey": TWELVE_DATA_API_KEY
        }
        try:
            quote_response = await client.get(f"{TWELVE_DATA_BASE_URL}/quote", params=quote_params)
            quote_response.raise_for_status()
            quote_data = quote_response.json()

            if "status" in quote_data and quote_data["status"] == "error":
                if "limit" in quote_data.get("message", "").lower():
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Twelve Data API rate limit exceeded: {quote_data['message']}"
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Stock '{ticker}' not found or data not available: {quote_data['message']}"
                    )
            
            if quote_data.get("symbol") is None or quote_data.get("close") is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Stock '{ticker}' not found or data not available."
                )

            current_price = float(quote_data["close"])
            price_change = float(quote_data["change"])
            change_percent = float(quote_data["percent_change"])

            formatted_change_percent = f"{round(change_percent, 2)}%"


        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Twelve Data API rate limit exceeded. Please try again after a minute."
                )
            else:
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Error fetching quote for {ticker}: {e.response.text}"
                )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Network error while fetching quote for {ticker}: {e}"
            )
        except (ValueError, KeyError) as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error parsing quote data from Twelve Data for {ticker}: {e}. Data might be malformed."
            )

        # --- 2. Fetch Historical Data (Last 30 Days) ---
        historical_params = {
            "symbol": ticker,
            "interval": "1day",
            "outputsize": 30,
            "apikey": TWELVE_DATA_API_KEY
        }
        historical_data_list = []
        try:
            historical_response = await client.get(f"{TWELVE_DATA_BASE_URL}/time_series", params=historical_params)
            historical_response.raise_for_status()
            historical_data_json = historical_response.json()

            if "status" in historical_data_json and historical_data_json["status"] == "error":
                print(f"Twelve Data historical data error for {ticker}: {historical_data_json['message']}")
            elif "values" in historical_data_json:
                for daily_data in reversed(historical_data_json["values"]):
                    date_str = daily_data["datetime"]
                    close_price = float(daily_data["close"])
                    historical_data_list.append(HistoricalData(date=date_str, close=close_price))
            else:
                print(f"No 'values' found for {ticker} or unexpected historical response format.")

        except httpx.HTTPStatusError as e:
            print(f"HTTP error fetching historical data for {ticker}: {e.response.text}")
        except httpx.RequestError as e:
            print(f"Network error while fetching historical data for {ticker}: {e}")
        except (ValueError, KeyError) as e:
            print(f"Error parsing historical data numeric values or keys for {ticker}: {e}.")


        # --- 3. Construct and Return StockData ---
        company_name = quote_data.get("name", ticker.upper())

        return StockData(
            symbol=ticker.upper(),
            name=company_name,
            price=current_price,
            change=round(price_change, 2),
            change_percent=formatted_change_percent,
            historical_data=historical_data_list
        )