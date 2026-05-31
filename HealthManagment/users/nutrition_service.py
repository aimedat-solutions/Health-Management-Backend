import time
import requests


OPENFOOD_API = "https://world.openfoodfacts.org/cgi/search.pl"
HEADERS = {
    "User-Agent": "MHealth-Backend/1.0 (admin@aimedatsolutions.com)"
}
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds


def fetch_nutrition_data(food_name: str) -> dict | None:
    params = {
        "search_terms": food_name,
        "json": 1,
        "page_size": 1,
    }

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(
                OPENFOOD_API, params=params, headers=HEADERS, timeout=10
            )
            if response.status_code == 200:
                return _parse_response(response.json())
            if response.status_code == 503 and attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
        except requests.RequestException:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
            return None

    return None


def _parse_response(data: dict) -> dict | None:
    products = data.get("products", [])
    if not products:
        return None
    p = products[0]
    nutriments = p.get("nutriments", {})
    return {
        "calories": nutriments.get("energy-kcal_100g"),
        "protein": nutriments.get("proteins_100g"),
        "carbohydrates": nutriments.get("carbohydrates_100g"),
        "fat": nutriments.get("fat_100g"),
        "fiber": nutriments.get("fiber_100g"),
        "sugar": nutriments.get("sugars_100g"),
        "saturated_fat": nutriments.get("saturated-fat_100g"),
        "trans_fat": nutriments.get("trans-fat_100g"),
        "cholesterol": nutriments.get("cholesterol_100g"),
        "sodium": nutriments.get("sodium_100g"),
        "serving_unit": "g",
        "serving_qty": 100,
        "ai_generated": True,
    }
