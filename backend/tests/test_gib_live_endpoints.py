"""
GIB Live Endpoints Test Suite
Tests for /api/gib/live/* endpoints
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials for plasiyer user
PLASIYER_CREDENTIALS = {
    "username": "sf_plasiyer",
    "password": "plasiyer123"
}


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for plasiyer user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json=PLASIYER_CREDENTIALS
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    assert "access_token" in data, "No access_token in response"
    return data["access_token"]


@pytest.fixture
def auth_headers(auth_token):
    """Headers with authorization token"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


class TestGibLiveStatus:
    """Tests for GET /api/gib/live/status endpoint"""
    
    def test_status_returns_200(self, auth_headers):
        """Status endpoint should return 200 with valid auth"""
        response = requests.get(
            f"{BASE_URL}/api/gib/live/status",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_status_returns_valid_structure(self, auth_headers):
        """Status response should have correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/gib/live/status",
            headers=auth_headers
        )
        data = response.json()
        
        # Check response structure
        assert "success" in data, "Response missing 'success' field"
        assert "data" in data, "Response missing 'data' field"
        assert data["success"] is True, "success should be True"
        
        # Check data structure
        status_data = data["data"]
        assert "state" in status_data, "Status data missing 'state' field"
        assert status_data["state"] in ["connected", "not_connected", "expired"], \
            f"Invalid state: {status_data['state']}"
    
    def test_status_requires_auth(self):
        """Status endpoint should require authentication"""
        response = requests.get(f"{BASE_URL}/api/gib/live/status")
        assert response.status_code in [401, 403], \
            f"Expected 401/403 without auth, got {response.status_code}"


class TestGibLiveDisconnect:
    """Tests for POST /api/gib/live/disconnect endpoint"""
    
    def test_disconnect_returns_200(self, auth_headers):
        """Disconnect endpoint should return 200 with valid auth"""
        response = requests.post(
            f"{BASE_URL}/api/gib/live/disconnect",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    def test_disconnect_returns_valid_structure(self, auth_headers):
        """Disconnect response should have correct structure"""
        response = requests.post(
            f"{BASE_URL}/api/gib/live/disconnect",
            headers=auth_headers
        )
        data = response.json()
        
        # Check response structure
        assert "success" in data, "Response missing 'success' field"
        assert "data" in data, "Response missing 'data' field"
        assert data["success"] is True, "success should be True"
        
        # After disconnect, state should be not_connected
        status_data = data["data"]
        assert "state" in status_data, "Status data missing 'state' field"
        assert status_data["state"] == "not_connected", \
            f"Expected 'not_connected' after disconnect, got {status_data['state']}"
    
    def test_disconnect_requires_auth(self):
        """Disconnect endpoint should require authentication"""
        response = requests.post(f"{BASE_URL}/api/gib/live/disconnect")
        assert response.status_code in [401, 403], \
            f"Expected 401/403 without auth, got {response.status_code}"


class TestGibLiveConnect:
    """Tests for POST /api/gib/live/connect endpoint"""
    
    def test_connect_requires_auth(self):
        """Connect endpoint should require authentication"""
        response = requests.post(
            f"{BASE_URL}/api/gib/live/connect",
            json={"username": "test", "password": "test", "mode": "live"}
        )
        assert response.status_code in [401, 403], \
            f"Expected 401/403 without auth, got {response.status_code}"
    
    def test_connect_validates_payload(self, auth_headers):
        """Connect endpoint should validate required fields"""
        # Missing username
        response = requests.post(
            f"{BASE_URL}/api/gib/live/connect",
            headers=auth_headers,
            json={"password": "test", "mode": "live"}
        )
        assert response.status_code == 422, \
            f"Expected 422 for missing username, got {response.status_code}"
        
        # Missing password
        response = requests.post(
            f"{BASE_URL}/api/gib/live/connect",
            headers=auth_headers,
            json={"username": "test", "mode": "live"}
        )
        assert response.status_code == 422, \
            f"Expected 422 for missing password, got {response.status_code}"


class TestGibLiveImport:
    """Tests for POST /api/gib/live/import/start endpoint"""
    
    def test_import_requires_auth(self):
        """Import endpoint should require authentication"""
        response = requests.post(
            f"{BASE_URL}/api/gib/live/import/start",
            json={"date_from": "2026-01-01", "date_to": "2026-01-07"}
        )
        assert response.status_code in [401, 403], \
            f"Expected 401/403 without auth, got {response.status_code}"
    
    def test_import_validates_date_format(self, auth_headers):
        """Import endpoint should validate date format or return not_connected error"""
        # Invalid date format - but may also fail due to not_connected state
        response = requests.post(
            f"{BASE_URL}/api/gib/live/import/start",
            headers=auth_headers,
            json={"date_from": "invalid", "date_to": "2026-01-07"}
        )
        # Should return 422 for validation error, 400 for bad request, or 409 for not_connected
        assert response.status_code in [400, 409, 422], \
            f"Expected 400/409/422 for invalid date or not_connected, got {response.status_code}"
    
    def test_import_when_not_connected(self, auth_headers):
        """Import should fail gracefully when not connected"""
        # First ensure we're disconnected
        requests.post(
            f"{BASE_URL}/api/gib/live/disconnect",
            headers=auth_headers
        )
        
        # Try to import
        response = requests.post(
            f"{BASE_URL}/api/gib/live/import/start",
            headers=auth_headers,
            json={"date_from": "2026-01-01", "date_to": "2026-01-07"}
        )
        
        # Should return error indicating not connected
        # 409 Conflict is the expected response for not_connected state
        assert response.status_code in [400, 403, 409, 422, 500], \
            f"Unexpected status code: {response.status_code}"
        
        # If 409, verify it's the not_connected error
        if response.status_code == 409:
            data = response.json()
            detail = data.get("detail", {})
            if isinstance(detail, dict):
                assert detail.get("code") == "not_connected", \
                    f"Expected 'not_connected' error code, got {detail}"


class TestGibRoleAuthorization:
    """Tests for role-based access control on GIB endpoints"""
    
    def test_customer_cannot_access_gib_status(self):
        """Customer role should not access GIB endpoints"""
        # Login as customer
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "sf_musteri", "password": "musteri123"}
        )
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            headers = {"Authorization": f"Bearer {token}"}
            
            # Try to access GIB status
            response = requests.get(
                f"{BASE_URL}/api/gib/live/status",
                headers=headers
            )
            
            # Should be forbidden for customer role
            assert response.status_code in [401, 403], \
                f"Customer should not access GIB endpoints, got {response.status_code}"
        else:
            pytest.skip("Customer login failed, skipping role test")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
