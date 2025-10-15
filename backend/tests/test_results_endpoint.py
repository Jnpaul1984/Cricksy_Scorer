from fastapi.testclient import TestClient
from backend.main import app  # Ensure this is your main FastAPI application file
from typing import Any

client = TestClient(app)

def test_results_endpoint():
    response = client.get("/games/results")  # making a request to the endpoint
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)  # Ensure results is a list
    
    # Further assertions assuming at least one result
    result: dict[str, Any] = results[0] # type: ignore
    assert "match_id" in result
    assert "winner" in result
    assert "team_a_score" in result
    assert "team_b_score" in result

    # Type checks
    assert isinstance(result["match_id"], str)
    assert isinstance(result["winner"], (str, type(None)))  # Winner can be None
    assert isinstance(result["team_a_score"], int)
    assert isinstance(result["team_b_score"], int)