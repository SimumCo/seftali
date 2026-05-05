"""
Warehouse Draft Page Backend API Tests
Tests for the Plasiyer Warehouse Draft API endpoint
Verifies the redesigned WarehouseDraftPage UI data requirements
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestWarehouseDraftAPIs:
    """Tests for Warehouse Draft related APIs"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - login as plasiyer"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login as plasiyer
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "username": "sf_plasiyer",
            "password": "plasiyer123"
        })
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        
        token = login_resp.json().get("access_token")
        assert token, "No access token received"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        print("Plasiyer login successful")
    
    # ==========================================
    # Warehouse Draft API Tests
    # ==========================================
    
    def test_warehouse_draft_returns_success(self):
        """GET /api/seftali/sales/warehouse-draft - should return success"""
        response = self.session.get(f"{BASE_URL}/api/seftali/sales/warehouse-draft")
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "data" in data
        print("Warehouse draft API returns success")
    
    def test_warehouse_draft_has_route_day(self):
        """Verify warehouse draft has route_day field"""
        response = self.session.get(f"{BASE_URL}/api/seftali/sales/warehouse-draft")
        
        assert response.status_code == 200
        data = response.json()["data"]
        
        assert "route_day" in data, "Missing route_day field"
        assert data["route_day"] in ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
        print(f"Route day: {data['route_day']}")
    
    def test_warehouse_draft_has_summary_counts(self):
        """Verify warehouse draft has summary count fields for UI cards"""
        response = self.session.get(f"{BASE_URL}/api/seftali/sales/warehouse-draft")
        
        assert response.status_code == 200
        data = response.json()["data"]
        
        # Required for summary cards
        assert "customer_count" in data, "Missing customer_count field"
        assert "order_customer_count" in data, "Missing order_customer_count field"
        assert "draft_customer_count" in data, "Missing draft_customer_count field"
        
        assert isinstance(data["customer_count"], int)
        assert isinstance(data["order_customer_count"], int)
        assert isinstance(data["draft_customer_count"], int)
        
        print(f"Summary counts - Customers: {data['customer_count']}, Orders: {data['order_customer_count']}, Drafts: {data['draft_customer_count']}")
    
    def test_warehouse_draft_has_order_items(self):
        """Verify warehouse draft has order_items array"""
        response = self.session.get(f"{BASE_URL}/api/seftali/sales/warehouse-draft")
        
        assert response.status_code == 200
        data = response.json()["data"]
        
        assert "order_items" in data, "Missing order_items field"
        assert isinstance(data["order_items"], list)
        print(f"Order items count: {len(data['order_items'])}")
    
    def test_warehouse_draft_order_item_structure(self):
        """Verify order_item has required fields for product cards"""
        response = self.session.get(f"{BASE_URL}/api/seftali/sales/warehouse-draft")
        
        assert response.status_code == 200
        data = response.json()["data"]
        order_items = data.get("order_items", [])
        
        if len(order_items) > 0:
            item = order_items[0]
            
            # Required fields for ProductCard component
            required_fields = [
                "product_id",
                "product_name",
                "plasiyer_stock",
                "warehouse_stock",
                "warehouse_skt",
                "order_qty",
                "draft_qty",
                "box_size",
                "final_qty"
            ]
            
            for field in required_fields:
                assert field in item, f"Missing required field: {field}"
            
            print(f"Order item structure verified: {list(item.keys())}")
    
    def test_warehouse_draft_plasiyer_stock_values(self):
        """Verify plasiyer_stock values for stock color logic"""
        response = self.session.get(f"{BASE_URL}/api/seftali/sales/warehouse-draft")
        
        assert response.status_code == 200
        order_items = response.json()["data"].get("order_items", [])
        
        stock_positive = 0
        stock_zero = 0
        
        for item in order_items:
            stock = item.get("plasiyer_stock", 0)
            assert isinstance(stock, (int, float)), f"plasiyer_stock must be numeric: {stock}"
            
            if stock > 0:
                stock_positive += 1
            else:
                stock_zero += 1
        
        print(f"Stock distribution - Positive: {stock_positive}, Zero: {stock_zero}")
    
    def test_warehouse_draft_box_size_values(self):
        """Verify box_size values for koli calculation"""
        response = self.session.get(f"{BASE_URL}/api/seftali/sales/warehouse-draft")
        
        assert response.status_code == 200
        order_items = response.json()["data"].get("order_items", [])
        
        for item in order_items:
            box_size = item.get("box_size", 1)
            assert isinstance(box_size, (int, float)), f"box_size must be numeric: {box_size}"
            assert box_size > 0, f"box_size must be positive: {box_size}"
        
        print(f"All {len(order_items)} items have valid box_size")
    
    def test_warehouse_draft_cutoff_info(self):
        """Verify cutoff time information is present"""
        response = self.session.get(f"{BASE_URL}/api/seftali/sales/warehouse-draft")
        
        assert response.status_code == 200
        data = response.json()["data"]
        
        # Cutoff info for alert display
        assert "is_after_cutoff" in data, "Missing is_after_cutoff field"
        assert "cutoff_time" in data, "Missing cutoff_time field"
        
        assert isinstance(data["is_after_cutoff"], bool)
        print(f"Cutoff info - After cutoff: {data['is_after_cutoff']}, Time: {data['cutoff_time']}")
    
    def test_warehouse_draft_submit_endpoint_exists(self):
        """Verify submit endpoint exists (don't actually submit)"""
        # Just verify the endpoint responds (even with empty data it should give validation error)
        response = self.session.post(
            f"{BASE_URL}/api/seftali/sales/warehouse-draft/submit",
            json={"items": [], "route_day": "WED", "note": ""}
        )
        
        # Should either succeed or give validation error, not 404
        assert response.status_code != 404, "Submit endpoint not found"
        print(f"Submit endpoint exists, status: {response.status_code}")
    
    def test_warehouse_draft_total_calculations(self):
        """Verify total calculations are present"""
        response = self.session.get(f"{BASE_URL}/api/seftali/sales/warehouse-draft")
        
        assert response.status_code == 200
        data = response.json()["data"]
        
        # Total fields
        assert "total_order_qty" in data, "Missing total_order_qty field"
        assert "total_products" in data, "Missing total_products field"
        
        print(f"Totals - Order qty: {data['total_order_qty']}, Products: {data['total_products']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
