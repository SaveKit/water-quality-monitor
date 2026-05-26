import requests
import json
from datetime import datetime, timedelta, timezone

BASE_URL = "http://127.0.0.1:8000"

def test_root():
    print("Testing Root API Endpoint...")
    response = requests.get(f"{BASE_URL}/")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    print("Root API Test: PASS\n")

def test_unauthorized():
    print("Testing Unauthorized access (Without Token)...")
    response = requests.get(f"{BASE_URL}/api/data/realtime")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 401
    print("Unauthorized Access Test: PASS\n")

def test_endpoints_with_mock_token():
    print("Testing API endpoints with mock token...")
    headers = {
        "Authorization": "Bearer mock_token"
    }

    # 1. Realtime
    print("1. Testing GET /api/data/realtime...")
    res_realtime = requests.get(f"{BASE_URL}/api/data/realtime", headers=headers)
    print(f"Status Code: {res_realtime.status_code}")
    print(f"Returned {len(res_realtime.json())} nodes.")
    assert res_realtime.status_code == 200

    # 2. WQI
    print("2. Testing GET /api/data/wqi...")
    res_wqi = requests.get(f"{BASE_URL}/api/data/wqi", headers=headers)
    print(f"Status Code: {res_wqi.status_code}")
    print(f"Response: {json.dumps(res_wqi.json(), indent=2, ensure_ascii=False)}")
    assert res_wqi.status_code == 200

    # 3. Forecast
    print("3. Testing GET /api/data/forecast...")
    res_forecast = requests.get(f"{BASE_URL}/api/data/forecast", headers=headers)
    print(f"Status Code: {res_forecast.status_code}")
    print(f"Response: {json.dumps(res_forecast.json(), indent=2, ensure_ascii=False)}")
    assert res_forecast.status_code == 200

    # 4. Historical
    print("4. Testing GET /api/data/historical...")
    now = datetime.now(timezone.utc)
    start_time = (now - timedelta(days=2)).isoformat()
    end_time = now.isoformat()
    params = {
        "node_id": "Node01",
        "sensor_type": "ph",
        "start_time": start_time,
        "end_time": end_time
    }
    res_history = requests.get(f"{BASE_URL}/api/data/historical", headers=headers, params=params)
    print(f"Status Code: {res_history.status_code}")
    print(f"Returned {len(res_history.json())} data points.")
    assert res_history.status_code == 200

    # 5. Export CSV
    print("5. Testing GET /api/data/export/csv...")
    res_csv = requests.get(f"{BASE_URL}/api/data/export/csv", headers=headers, params=params)
    print(f"Status Code: {res_csv.status_code}")
    print(f"Headers: {res_csv.headers}")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers.get("content-type", "")

    # 6. Alerts
    print("6. Testing GET /api/data/alerts...")
    res_alerts = requests.get(f"{BASE_URL}/api/data/alerts", headers=headers)
    print(f"Status Code: {res_alerts.status_code}")
    print(f"Returned {len(res_alerts.json())} alerts.")
    assert res_alerts.status_code == 200

    print("All endpoints with mock token: PASS\n")

if __name__ == "__main__":
    try:
        test_root()
        test_unauthorized()
        test_endpoints_with_mock_token()
        print("="*40)
        print("ALL BACKEND API TESTS COMPLETED SUCCESSFULLY!")
        print("="*40)
    except AssertionError as e:
        print("TEST ASSERTION FAILED!")
        raise e
    except Exception as e:
        print(f"Error executing API tests: {e}")
        raise e
