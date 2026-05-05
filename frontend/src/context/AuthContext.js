import React, { createContext, useContext, useState, useEffect } from 'react';
import { authAPI, customerAuthAPI } from '../services/api';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    const token = localStorage.getItem('token');
    const customerToken = localStorage.getItem('customer_token');
    const customerUserRaw = localStorage.getItem('customer_user');

    if (token) {
      try {
        const response = await authAPI.getMe();
        setUser(response.data);
      } catch (error) {
        console.error('Auth check failed:', error);
        localStorage.removeItem('token');
        localStorage.removeItem('user');
      }
    } else if (customerToken && customerUserRaw) {
      try {
        setUser(JSON.parse(customerUserRaw));
      } catch (error) {
        console.error('Customer auth check failed:', error);
        localStorage.removeItem('customer_token');
        localStorage.removeItem('customer_user');
      }
    }
    setLoading(false);
  };

  const login = async (username, password) => {
    try {
      const response = await authAPI.login({ username, password });
      const { access_token, user: userData } = response.data;
      localStorage.removeItem('customer_token');
      localStorage.removeItem('customer_user');
      localStorage.setItem('token', access_token);
      localStorage.setItem('user', JSON.stringify(userData));
      setUser(userData);
      return { success: true };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Login failed',
      };
    }
  };

  const loginCustomer = async (username, password) => {
    try {
      const response = await customerAuthAPI.login({ username, password });
      const data = response.data?.data || {};
      const customerUser = {
        role: 'customer',
        customer_id: data.customer_id,
        user_id: data.user_id,
        username: data.username,
        must_change_password: data.must_change_password,
        business_name: data.customer?.business_name,
        customer_type: data.customer?.customer_type,
      };

      localStorage.removeItem('token');
      localStorage.removeItem('user');
      localStorage.setItem('customer_token', data.token);
      localStorage.setItem('customer_user', JSON.stringify(customerUser));
      setUser(customerUser);
      return { success: true, data };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || error.response?.data?.message || 'Customer login failed',
      };
    }
  };

  const markCustomerPasswordChanged = () => {
    const customerUserRaw = localStorage.getItem('customer_user');
    if (!customerUserRaw) return;

    try {
      const customerUser = JSON.parse(customerUserRaw);
      const updatedUser = { ...customerUser, must_change_password: false };
      localStorage.setItem('customer_user', JSON.stringify(updatedUser));
      setUser(updatedUser);
    } catch (error) {
      console.error('Customer password change sync failed:', error);
    }
  };

  const logout = () => {
    const isCustomerSession = user?.role === 'customer' || !!localStorage.getItem('customer_token');
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('customer_token');
    localStorage.removeItem('customer_user');
    setUser(null);
    window.location.href = isCustomerSession ? '/customer-login' : '/login';
  };

  const value = {
    user,
    login,
    loginCustomer,
    markCustomerPasswordChanged,
    logout,
    loading,
    isAuthenticated: !!user,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
