"""
Customer Auth API Tests
Tests for customer login and change password flows
"""
import pytest
import requests
import os
from dotenv import dotenv_values

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
DEFAULT_CUSTOMER_PASSWORD = dotenv_values('/app/backend/.env')['DEFAULT_CUSTOMER_PASSWORD']


class TestCustomerLogin:
    """Customer login endpoint tests"""

    def test_customer_login_success(self):
        """Test successful customer login with valid credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/customer/login",
            json={"username": "8777777777", "password": DEFAULT_CUSTOMER_PASSWORD}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") is True
        assert "data" in data
        
        login_data = data["data"]
        assert "token" in login_data
        assert "customer_id" in login_data
        assert "user_id" in login_data
        assert "username" in login_data
        assert login_data["username"] == "8777777777"
        assert "must_change_password" in login_data
        assert "customer" in login_data
        assert "business_name" in login_data["customer"]

    def test_customer_login_invalid_password(self):
        """Test login with wrong password"""
        response = requests.post(
            f"{BASE_URL}/api/auth/customer/login",
            json={"username": "8777777777", "password": "wrongpassword"}
        )
        assert response.status_code == 401

    def test_customer_login_nonexistent_user(self):
        """Test login with non-existent username"""
        response = requests.post(
            f"{BASE_URL}/api/auth/customer/login",
            json={"username": "9999999999", "password": DEFAULT_CUSTOMER_PASSWORD}
        )
        assert response.status_code == 401

    def test_customer_login_empty_username(self):
        """Test login with empty username"""
        response = requests.post(
            f"{BASE_URL}/api/auth/customer/login",
            json={"username": "", "password": DEFAULT_CUSTOMER_PASSWORD}
        )
        assert response.status_code == 400

    def test_customer_login_empty_password(self):
        """Test login with empty password"""
        response = requests.post(
            f"{BASE_URL}/api/auth/customer/login",
            json={"username": "8777777777", "password": ""}
        )
        assert response.status_code == 400


class TestCustomerChangePassword:
    """Customer change password endpoint tests"""

    def _get_token(self, password=DEFAULT_CUSTOMER_PASSWORD):
        """Get a valid customer token for testing"""
        response = requests.post(
            f"{BASE_URL}/api/auth/customer/login",
            json={"username": "8444444444", "password": password}
        )
        if response.status_code == 200:
            return response.json()["data"]["token"]
        return None

    def test_change_password_success(self):
        """Test successful password change"""
        token = self._get_token(DEFAULT_CUSTOMER_PASSWORD)
        if not token:
            pytest.skip("Could not get customer token")
            
        response = requests.post(
            f"{BASE_URL}/api/auth/customer/change-password",
            json={
                "current_password": DEFAULT_CUSTOMER_PASSWORD,
                "new_password": "NewPass123"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("success") is True
        assert data.get("must_change_password") is False
        
        # Reset password back for future tests
        new_token = self._get_token("NewPass123")
        if new_token:
            requests.post(
                f"{BASE_URL}/api/auth/customer/change-password",
                json={
                    "current_password": "NewPass123",
                    "new_password": DEFAULT_CUSTOMER_PASSWORD
                },
                headers={"Authorization": f"Bearer {new_token}"}
            )

    def test_change_password_wrong_current(self):
        """Test change password with wrong current password"""
        token = self._get_token(DEFAULT_CUSTOMER_PASSWORD)
        if not token:
            pytest.skip("Could not get customer token")
            
        response = requests.post(
            f"{BASE_URL}/api/auth/customer/change-password",
            json={
                "current_password": "wrongpassword",
                "new_password": "NewPass123"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401

    def test_change_password_same_password(self):
        """Test change password with same password"""
        token = self._get_token(DEFAULT_CUSTOMER_PASSWORD)
        if not token:
            pytest.skip("Could not get customer token")
            
        response = requests.post(
            f"{BASE_URL}/api/auth/customer/change-password",
            json={
                "current_password": DEFAULT_CUSTOMER_PASSWORD,
                "new_password": DEFAULT_CUSTOMER_PASSWORD
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 400

    def test_change_password_weak_password(self):
        """Test change password with weak password (no letter or number)"""
        token = self._get_token(DEFAULT_CUSTOMER_PASSWORD)
        if not token:
            pytest.skip("Could not get customer token")
            
        response = requests.post(
            f"{BASE_URL}/api/auth/customer/change-password",
            json={
                "current_password": DEFAULT_CUSTOMER_PASSWORD,
                "new_password": "12345678"  # No letters
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 400

    def test_change_password_no_auth(self):
        """Test change password without authentication"""
        response = requests.post(
            f"{BASE_URL}/api/auth/customer/change-password",
            json={
                "current_password": DEFAULT_CUSTOMER_PASSWORD,
                "new_password": "NewPass123"
            }
        )
        assert response.status_code == 403  # No auth header


class TestPasswordChangeGuardMiddleware:
    """Test middleware that blocks customer requests when password change is required"""

    def test_middleware_blocks_when_must_change_password(self):
        """Test that middleware blocks requests when must_change_password is True"""
        # Login with user that has must_change_password=True
        login_response = requests.post(
            f"{BASE_URL}/api/auth/customer/login",
            json={"username": "8777777777", "password": DEFAULT_CUSTOMER_PASSWORD}
        )
        assert login_response.status_code == 200
        token = login_response.json()["data"]["token"]
        
        # Try to access a protected endpoint
        profile_response = requests.get(
            f"{BASE_URL}/api/seftali/customer/profile",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Should be blocked with PASSWORD_CHANGE_REQUIRED
        assert profile_response.status_code == 403
        data = profile_response.json()
        assert data.get("error") == "PASSWORD_CHANGE_REQUIRED"


class TestEmployeeLoginNotBroken:
    """Verify employee login still works"""

    def test_employee_login_success(self):
        """Test employee login with valid credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "sf_plasiyer", "password": "plasiyer123"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["username"] == "sf_plasiyer"

    def test_employee_auth_me(self):
        """Test employee /auth/me endpoint"""
        # Login first
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "sf_plasiyer", "password": "plasiyer123"}
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        # Get me
        me_response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert me_response.status_code == 200
        data = me_response.json()
        assert data["username"] == "sf_plasiyer"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
