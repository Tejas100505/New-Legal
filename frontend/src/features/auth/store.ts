/**
 * Authentication Zustand store.
 * Manages user session, JWT token, and login/logout actions.
 * Persisted to localStorage for session persistence.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User } from '@/types';

import api from '@/lib/api';

interface AuthStore {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: {
    email: string;
    password: string;
    fullName: string;
    firm?: string;
    barNumber?: string;
  }) => Promise<void>;
  logout: () => void;
  setLoading: (loading: boolean) => void;
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,

      login: async (email: string, password: string) => {
        set({ isLoading: true });
        try {
          const response = await api.post('/auth/login', { email, password });
          const { access_token, user: apiUser } = response.data;
          
          const user: User = {
            id: apiUser.id,
            email: apiUser.email,
            name: apiUser.full_name,
            role: apiUser.role,
            firm: apiUser.firm || 'Apex Legal LLP',
            barNumber: apiUser.bar_number || '',
            createdAt: apiUser.created_at || new Date().toISOString(),
            lastLoginAt: new Date().toISOString(),
          };

          set({
            user,
            token: access_token,
            isAuthenticated: true,
            isLoading: false,
          });

          localStorage.setItem('auth_token', access_token);
        } catch (err: any) {
          set({ isLoading: false });
          const msg = err.response?.data?.detail || err.message || 'Authentication failed';
          throw new Error(msg);
        }
      },

      register: async (data: {
        email: string;
        password: string;
        fullName: string;
        firm?: string;
        barNumber?: string;
      }) => {
        set({ isLoading: true });
        try {
          await api.post('/auth/register', {
            email: data.email,
            password: data.password,
            full_name: data.fullName,
            firm: data.firm || undefined,
            bar_number: data.barNumber || undefined,
          });

          // Automatically log the newly created user in
          const response = await api.post('/auth/login', {
            email: data.email,
            password: data.password,
          });
          const { access_token, user: apiUser } = response.data;

          const user: User = {
            id: apiUser.id,
            email: apiUser.email,
            name: apiUser.full_name,
            role: apiUser.role,
            firm: apiUser.firm || 'Apex Legal LLP',
            barNumber: apiUser.bar_number || '',
            createdAt: apiUser.created_at || new Date().toISOString(),
            lastLoginAt: new Date().toISOString(),
          };

          set({
            user,
            token: access_token,
            isAuthenticated: true,
            isLoading: false,
          });

          localStorage.setItem('auth_token', access_token);
        } catch (err: any) {
          set({ isLoading: false });
          const msg = err.response?.data?.detail || err.message || 'Registration failed';
          throw new Error(msg);
        }
      },

      logout: () => {
        api.post('/auth/logout').catch(() => {});
        localStorage.removeItem('auth_token');
        set({
          user: null,
          token: null,
          isAuthenticated: false,
          isLoading: false,
        });
      },

      setLoading: (loading: boolean) => set({ isLoading: loading }),
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
