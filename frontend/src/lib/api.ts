import axios from 'axios';
import toast from 'react-hot-toast';

/**
 * Configured Axios instance for backend API calls.
 * In development, Vite proxies /api to localhost:8000.
 * In production, nginx proxies /api to the backend container.
 */
const api = axios.create({
  baseURL: '/api/v1',
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export function getAuthToken(): string | null {
  const direct = localStorage.getItem('auth_token');
  if (direct) return direct;
  try {
    const raw = localStorage.getItem('auth-storage');
    if (raw) {
      const parsed = JSON.parse(raw);
      const token = parsed?.state?.token;
      if (token) {
        localStorage.setItem('auth_token', token);
        return token;
      }
    }
  } catch {}
  return null;
}

let last401Time = 0;

// ── Request interceptor: attach auth token if available ─────────────────────
api.interceptors.request.use(
  (config) => {
    const token = getAuthToken();
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
        try {
          const raw = localStorage.getItem('auth-storage');
          if (raw) {
            const parsed = JSON.parse(raw);
            if (parsed?.state) {
              parsed.state.token = null;
              parsed.state.user = null;
              parsed.state.isAuthenticated = false;
              localStorage.setItem('auth-storage', JSON.stringify(parsed));
            }
          }
        } catch {}

        if (typeof window !== 'undefined') {
          window.dispatchEvent(new Event('auth:unauthorized'));
          if (window.location.pathname !== '/login') {
            window.location.href = '/login';
          }
        }
      } else if (status === 403) {
        message = 'You do not have permission to perform this action.';
      } else if (status === 404) {
        message = 'The requested resource was not found.';
      } else if (status === 422) {
        message = 'Invalid data provided.';
      } else if (status >= 500) {
        message = 'Server error. Please try again later.';
      }

      const now = Date.now();
      const is401Spam = status === 401 && now - last401Time < 3000;
      if (status === 401) {
        last401Time = now;
      }

      const isSuppressed = Boolean(
        is401Spam ||
        error.config?.suppressErrorToast ||
        (status === 404 && error.config?.suppress404Toast)
      );

      if (!isSuppressed) {
        console.error(`[API Error ${status}]:`, data);
        toast.error(message);
      }

      return Promise.reject({
        status,
        message,
        data,
      });
    }
    
    // Network error
    if (!error.config?.suppressErrorToast) {
      console.error('[API Network Error]:', error.message);
      toast.error('Network error — please check your connection');
    }
    
    return Promise.reject({
      status: 0,
      message: error.message || 'Network error — please check your connection',
    });
  }
);

export default api;
