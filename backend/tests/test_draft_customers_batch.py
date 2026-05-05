"""
Test Draft Customers Management Feature
- GET /api/draft-customers?salespersonId=
- POST /api/draft-customers/:id/approve
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestDraftCustomersAPI:
    """Draft Customers API tests for Plasiyer batch"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login as plasiyer user"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as plasiyer
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "username": "sf_plasiyer",
            "password": "plasiyer123"
        })
        
        if login_response.status_code != 200:
            pytest.skip("Plasiyer login failed - skipping tests")
        
        login_data = login_response.json()
        self.token = login_data.get("access_token")
        self.user = login_data.get("user", {})
        self.salesperson_id = self.user.get("id")
        
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        print(f"Logged in as plasiyer with id: {self.salesperson_id}")
    
    def test_plasiyer_login_success(self):
        """Test that plasiyer login works"""
        assert self.token is not None
        assert self.salesperson_id is not None
        print(f"PASS: Plasiyer login successful, user_id={self.salesperson_id}")
    
    def test_get_draft_customers_success(self):
        """Test GET /api/draft-customers?salespersonId= returns 200"""
        response = self.session.get(
            f"{BASE_URL}/api/draft-customers",
            params={"salespersonId": self.salesperson_id}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "success" in data
        assert data["success"] == True
        assert "data" in data
        
        # Data should be a list
        items = data["data"]
        assert isinstance(items, list), f"Expected list, got {type(items)}"
        
        print(f"PASS: GET /api/draft-customers returned {len(items)} items")
        
        # If there are items, verify structure
        if len(items) > 0:
            item = items[0]
            # Check expected fields exist
            expected_fields = ["id", "business_name", "status"]
            for field in expected_fields:
                assert field in item, f"Missing field: {field}"
            print(f"PASS: Draft customer item has expected fields: {list(item.keys())}")
    
    def test_get_draft_customers_without_salesperson_id(self):
        """Test GET /api/draft-customers without salespersonId returns 422"""
        response = self.session.get(f"{BASE_URL}/api/draft-customers")
        
        # Should return 422 (validation error) since salespersonId is required
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("PASS: GET /api/draft-customers without salespersonId returns 422")
    
    def test_get_draft_customers_wrong_salesperson_id(self):
        """Test GET /api/draft-customers with wrong salespersonId returns 403"""
        response = self.session.get(
            f"{BASE_URL}/api/draft-customers",
            params={"salespersonId": "wrong-id-12345"}
        )
        
        # Should return 403 (forbidden) since user can only see their own data
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("PASS: GET /api/draft-customers with wrong salespersonId returns 403")
    
    def test_approve_draft_customer_not_found(self):
        """Test POST /api/draft-customers/:id/approve with non-existent id returns 404"""
        response = self.session.post(
            f"{BASE_URL}/api/draft-customers/nonexistent-id-12345/approve",
            json={
                "customer_type": "retail",
                "risk_limit": 10000,
                "balance": 0,
                "phone": "5551234567",
                "address": "Test Address"
            }
        )
        
        # Should return 404 (not found)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("PASS: POST /api/draft-customers/:id/approve with non-existent id returns 404")
    
    def test_approve_draft_customer_validation(self):
        """Test POST /api/draft-customers/:id/approve validates payload"""
        # First get draft customers to find a real ID if available
        response = self.session.get(
            f"{BASE_URL}/api/draft-customers",
            params={"salespersonId": self.salesperson_id}
        )
        
        if response.status_code != 200:
            pytest.skip("Could not get draft customers")
        
        items = response.json().get("data", [])
        
        if len(items) == 0:
            # No draft customers to test with, test with fake ID
            response = self.session.post(
                f"{BASE_URL}/api/draft-customers/fake-id/approve",
                json={}  # Empty payload
            )
            # Should return 422 (validation error) or 404 (not found)
            assert response.status_code in [422, 404], f"Expected 422 or 404, got {response.status_code}"
            print("PASS: Empty payload returns validation error or not found")
        else:
            # Test with real draft customer
            draft_id = items[0]["id"]
            response = self.session.post(
                f"{BASE_URL}/api/draft-customers/{draft_id}/approve",
                json={}  # Empty payload
            )
            # Should return 422 (validation error)
            assert response.status_code == 422, f"Expected 422, got {response.status_code}"
            print("PASS: Empty payload returns validation error")


class TestDraftCustomersDataStructure:
    """Test draft customer data structure and fields"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login as plasiyer user"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as plasiyer
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "username": "sf_plasiyer",
            "password": "plasiyer123"
        })
        
        if login_response.status_code != 200:
            pytest.skip("Plasiyer login failed - skipping tests")
        
        login_data = login_response.json()
        self.token = login_data.get("access_token")
        self.user = login_data.get("user", {})
        self.salesperson_id = self.user.get("id")
        
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_draft_customer_fields(self):
        """Test that draft customer items have expected fields"""
        response = self.session.get(
            f"{BASE_URL}/api/draft-customers",
            params={"salespersonId": self.salesperson_id}
        )
        
        assert response.status_code == 200
        items = response.json().get("data", [])
        
        if len(items) == 0:
            print("INFO: No draft customers found - skipping field validation")
            return
        
        item = items[0]
        
        # Check for expected fields based on requirements
        expected_fields = [
            "id",
            "business_name",
            "status"
        ]
        
        # Optional fields that should be present
        optional_fields = [
            "tax_number",
            "tc_no",
            "invoice_count",
            "last_invoice_date",
            "total_amount"
        ]
        
        for field in expected_fields:
            assert field in item, f"Missing required field: {field}"
        
        print(f"PASS: Draft customer has required fields")
        print(f"INFO: Draft customer fields: {list(item.keys())}")
        
        # Check at least one identifier exists
        has_identifier = "tax_number" in item or "tc_no" in item
        print(f"INFO: Has tax_number or tc_no: {has_identifier}")


class TestNoAuthAccess:
    """Test that draft customers API requires authentication"""
    
    def test_get_draft_customers_no_auth(self):
        """Test GET /api/draft-customers without auth returns 401 or 403"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        response = session.get(
            f"{BASE_URL}/api/draft-customers",
            params={"salespersonId": "some-id"}
        )
        
        # Accept both 401 (Unauthorized) and 403 (Forbidden) as valid auth rejection
        assert response.status_code in [401, 403], f"Expected 401 or 403, got {response.status_code}"
        print(f"PASS: GET /api/draft-customers without auth returns {response.status_code}")
    
    def test_approve_draft_customer_no_auth(self):
        """Test POST /api/draft-customers/:id/approve without auth returns 401 or 403"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        response = session.post(
            f"{BASE_URL}/api/draft-customers/some-id/approve",
            json={
                "customer_type": "retail",
                "risk_limit": 10000,
                "balance": 0,
                "phone": "5551234567",
                "address": "Test Address"
            }
        )
        
        # Accept both 401 (Unauthorized) and 403 (Forbidden) as valid auth rejection
        assert response.status_code in [401, 403], f"Expected 401 or 403, got {response.status_code}"
        print(f"PASS: POST /api/draft-customers/:id/approve without auth returns {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
