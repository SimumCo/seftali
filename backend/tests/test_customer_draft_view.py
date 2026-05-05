"""
Customer DraftView API Tests
Tests for the customer order screen redesign - verifies backend APIs
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestCustomerAuth:
    """Customer authentication tests"""
    
    def test_customer_login_success(self):
        """Test customer login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "sf_musteri",
            "password": "musteri123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "customer"
        print(f"✓ Customer login successful: {data['user']['full_name']}")


class TestCustomerDraftAPIs:
    """Customer draft/order APIs tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token for customer"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "sf_musteri",
            "password": "musteri123"
        })
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            pytest.skip("Customer authentication failed")
    
    def test_get_customer_profile(self):
        """Test customer profile API - returns route_plan with days"""
        response = requests.get(f"{BASE_URL}/api/seftali/customer/profile", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "data" in data
        profile = data["data"]
        assert "route_plan" in profile
        assert "days" in profile["route_plan"]
        print(f"✓ Customer profile: {profile['name']}, route days: {profile['route_plan']['days']}")
    
    def test_get_customer_draft(self):
        """Test customer draft API - returns products with suggested_qty"""
        response = requests.get(f"{BASE_URL}/api/seftali/customer/draft", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "data" in data
        draft = data["data"]
        
        # Verify draft structure
        assert "items" in draft
        assert "route_info" in draft
        
        # Verify route_info has next delivery info
        route_info = draft["route_info"]
        assert "next_route_weekday" in route_info
        print(f"✓ Draft route info: next delivery {route_info['next_route_weekday']}")
        
        # Verify items have required fields
        items = draft["items"]
        assert len(items) > 0, "Draft should have at least one item"
        
        for item in items:
            assert "product_id" in item
            assert "product_name" in item
            assert "suggested_qty" in item
            # Verify suggested_qty is a number
            assert isinstance(item["suggested_qty"], (int, float))
            print(f"  - {item['product_name']}: suggested_qty={item['suggested_qty']}")
    
    def test_get_customer_products(self):
        """Test customer products API"""
        response = requests.get(f"{BASE_URL}/api/seftali/customer/products", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "data" in data
        products = data["data"]
        assert len(products) > 0
        print(f"✓ Customer products: {len(products)} products available")
    
    def test_get_consumption_summary(self):
        """Test consumption summary API"""
        response = requests.get(f"{BASE_URL}/api/seftali/customer/daily-consumption/summary", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        print(f"✓ Consumption summary retrieved")
    
    def test_working_copy_flow(self):
        """Test working copy start/update/submit flow"""
        # Start working copy
        response = requests.post(f"{BASE_URL}/api/seftali/customer/working-copy/start", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        working_copy_id = data["data"]["id"]
        print(f"✓ Working copy started: {working_copy_id}")
        
        # Update working copy with items
        items = [
            {"product_id": "AILEM_AYRAN_2L_TEST", "user_qty": 10, "removed": False}
        ]
        response = requests.patch(
            f"{BASE_URL}/api/seftali/customer/working-copy/{working_copy_id}",
            json=items,
            headers=self.headers
        )
        assert response.status_code == 200
        print(f"✓ Working copy updated with {len(items)} items")
        
        # Note: Not submitting to avoid creating actual orders in test
        print("✓ Working copy flow verified (submit skipped to avoid test data)")


class TestDraftDataValidation:
    """Validate draft data matches expected format for UI"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token for customer"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "sf_musteri",
            "password": "musteri123"
        })
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            pytest.skip("Customer authentication failed")
    
    def test_draft_items_have_no_plasiyer_only_fields(self):
        """Verify draft items don't expose plasiyer-only technical info"""
        response = requests.get(f"{BASE_URL}/api/seftali/customer/draft", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        items = data["data"]["items"]
        
        # These fields should NOT be in customer draft (plasiyer-only)
        plasiyer_only_fields = ["depot_stock", "plasiyer_stock", "logistics_info"]
        
        for item in items:
            for field in plasiyer_only_fields:
                assert field not in item, f"Plasiyer-only field '{field}' should not be in customer draft"
        
        print("✓ Draft items don't contain plasiyer-only technical info")
    
    def test_draft_items_have_required_customer_fields(self):
        """Verify draft items have all required fields for customer UI"""
        response = requests.get(f"{BASE_URL}/api/seftali/customer/draft", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        items = data["data"]["items"]
        
        # Required fields for customer UI
        required_fields = ["product_id", "product_name", "suggested_qty"]
        
        for item in items:
            for field in required_fields:
                assert field in item, f"Required field '{field}' missing from draft item"
        
        print("✓ Draft items have all required customer fields")
    
    def test_route_info_has_next_delivery_day(self):
        """Verify route_info includes next delivery day for UI badge"""
        response = requests.get(f"{BASE_URL}/api/seftali/customer/draft", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        route_info = data["data"]["route_info"]
        
        assert "next_route_weekday" in route_info
        assert route_info["next_route_weekday"] is not None
        print(f"✓ Next delivery day: {route_info['next_route_weekday']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
