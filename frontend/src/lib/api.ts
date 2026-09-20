import axios from 'axios';
import toast from 'react-hot-toast';

/**
 * Configured Axios instance for backend API calls.
 * In development, Vite proxies /api to localhost:8000.
 * In production, nginx proxies /api to the backend container.
 */
const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ── Request interceptor: attach auth token if available ─────────────────────
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ── Response interceptor: standardized error handling ────────────────────────
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      const { status, data } = error.response;
      
      let message = data?.detail || 'An unexpected error occurred';
      if (status === 401) {
        message = 'Session expired. Please log in again.';
        localStorage.removeItem('auth_token');
      } else if (status === 403) {
        message = 'You do not have permission to perform this action.';
      } else if (status === 404) {
        message = 'The requested resource was not found.';
      } else if (status === 422) {
        message = 'Invalid data provided.';
      } else if (status >= 500) {
        message = 'Server error. Please try again later.';
      }

      console.error(`[API Error ${status}]:`, data);
      toast.error(message);

      return Promise.reject({
        status,
        message,
        data,
      });
    }
    
    // Network error
    console.error('[API Network Error]:', error.message);
    toast.error('Network error — please check your connection');
    
    return Promise.reject({
      status: 0,
      message: 'Network error — please check your connection',
    });
  }
);

export default api;
