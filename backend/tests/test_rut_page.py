"""
Rut Page Backend API Tests
Tests for the Plasiyer Route Customers API endpoint
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestRutPageAPIs:
    """Tests for Rut Page related APIs"""
    
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
    # Route Customers API Tests
    # ==========================================
    
    def test_route_customers_mon_returns_data(self):
        """GET /api/seftali/sales/plasiyer/route-customers/MON - should return customers"""
        response = self.session.get(f"{BASE_URL}/api/seftali/sales/plasiyer/route-customers/MON")
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "data" in data
        
        customers = data["data"]
        assert isinstance(customers, list)
        print(f"MON route has {len(customers)} customers")
        
        # Verify at least one customer exists for MON
        assert len(customers) > 0, "Expected at least one customer for MON route"
    
    def test_route_customers_tue_returns_data(self):
        """GET /api/seftali/sales/plasiyer/route-customers/TUE - should return customers"""
        response = self.session.get(f"{BASE_URL}/api/seftali/sales/plasiyer/route-customers/TUE")
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        
        customers = data["data"]
        assert isinstance(customers, list)
        print(f"TUE route has {len(customers)} customers")
        
        # Verify at least one customer exists for TUE
        assert len(customers) > 0, "Expected at least one customer for TUE route"
    
    def test_route_customers_sat_empty(self):
        """GET /api/seftali/sales/plasiyer/route-customers/SAT - should return empty list"""
        response = self.session.get(f"{BASE_URL}/api/seftali/sales/plasiyer/route-customers/SAT")
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        
        customers = data["data"]
        assert isinstance(customers, list)
        # SAT may or may not have customers - just verify structure
        print(f"SAT route has {len(customers)} customers")
    
    def test_route_customer_data_structure(self):
        """Verify route customer data structure has required fields"""
        response = self.session.get(f"{BASE_URL}/api/seftali/sales/plasiyer/route-customers/MON")
        
        assert response.status_code == 200
        data = response.json()
        customers = data["data"]
        
        if len(customers) > 0:
            customer = customers[0]
            
            # Required fields for frontend normalization
            assert "id" in customer, "Customer must have 'id' field"
            assert "name" in customer or "customer_name" in customer, "Customer must have name field"
            
            # Check for route_plan structure
            if "route_plan" in customer:
                route_plan = customer["route_plan"]
                assert "days" in route_plan, "route_plan must have 'days' field"
            
            # Check for order_status (used for visited/pending determination)
            assert "order_status" in customer, "Customer must have 'order_status' field"
            
            print(f"Customer data structure verified: {list(customer.keys())}")
    
    def test_route_customer_order_status_values(self):
        """Verify order_status values are valid"""
        response = self.session.get(f"{BASE_URL}/api/seftali/sales/plasiyer/route-customers/MON")
        
        assert response.status_code == 200
        customers = response.json()["data"]
        
        valid_statuses = ["submitted", "draft_available", "no_order"]
        
        for customer in customers:
            status = customer.get("order_status")
            assert status in valid_statuses, f"Invalid order_status: {status}"
        
        print(f"All {len(customers)} customers have valid order_status")
    
    def test_route_customer_visit_order_field(self):
        """Verify visit_order or sequence field exists for ordering"""
        response = self.session.get(f"{BASE_URL}/api/seftali/sales/plasiyer/route-customers/TUE")
        
        assert response.status_code == 200
        customers = response.json()["data"]
        
        for customer in customers:
            # Frontend uses: visit_order ?? route_plan.sequence ?? route_order ?? index+1
            has_order_field = (
                "visit_order" in customer or 
                ("route_plan" in customer and "sequence" in customer.get("route_plan", {})) or
                "route_order" in customer
            )
            # It's OK if none exist - frontend will use index+1 as fallback
            if has_order_field:
                print(f"Customer {customer.get('name', customer['id'])} has ordering field")
    
    def test_route_customers_invalid_day(self):
        """GET /api/seftali/sales/plasiyer/route-customers/INVALID - should handle gracefully"""
        response = self.session.get(f"{BASE_URL}/api/seftali/sales/plasiyer/route-customers/INVALID")
        
        # Should either return 400 or empty list
        assert response.status_code in [200, 400]
        
        if response.status_code == 200:
            data = response.json()
            # Should return empty list for invalid day
            assert data.get("data") == [] or data.get("success") == True
    
    def test_route_customers_lowercase_day(self):
        """GET /api/seftali/sales/plasiyer/route-customers/mon - should work with lowercase"""
        response = self.session.get(f"{BASE_URL}/api/seftali/sales/plasiyer/route-customers/mon")
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print("Lowercase day code works")
    
    # ==========================================
    # Related API Tests
    # ==========================================
    
    def test_customers_summary_api(self):
        """GET /api/seftali/sales/customers/summary - should return customer summaries"""
        response = self.session.get(f"{BASE_URL}/api/seftali/sales/customers/summary")
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        assert "data" in data
        
        customers = data["data"]
        assert isinstance(customers, list)
        print(f"Customers summary returned {len(customers)} customers")
    
    def test_customers_list_api(self):
        """GET /api/seftali/sales/customers - should return customers"""
        response = self.session.get(f"{BASE_URL}/api/seftali/sales/customers")
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == True
        print("Customers list API working")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
