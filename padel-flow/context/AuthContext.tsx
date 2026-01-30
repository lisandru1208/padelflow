// context/AuthContext.tsx
// Gère l'état d'authentification dans toute l'application

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { login as apiLogin, register as apiRegister, LoginResponse } from '../services/api';

interface AuthContextType {
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  error: string | null;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_KEY = 'padelflow_token';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Charger le token au démarrage de l'app
  useEffect(() => {
    loadToken();
  }, []);

  const loadToken = async () => {
    try {
      const storedToken = await AsyncStorage.getItem(TOKEN_KEY);
      if (storedToken) {
        setToken(storedToken);
      }
    } catch (e) {
      console.error('Erreur lors du chargement du token:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const response: LoginResponse = await apiLogin(email, password);
      const newToken = response.access_token;
      await AsyncStorage.setItem(TOKEN_KEY, newToken);
      setToken(newToken);
    } catch (e: any) {
      setError(e.message || 'Échec de la connexion');
      throw e;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (email: string, password: string) => {
    setIsLoading(true);
    setError(null);
    try {
      await apiRegister(email, password);
      // Après inscription réussie, connecter automatiquement
      await login(email, password);
    } catch (e: any) {
      setError(e.message || "Échec de l'inscription");
      throw e;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    try {
      await AsyncStorage.removeItem(TOKEN_KEY);
      setToken(null);
    } catch (e) {
      console.error('Erreur lors de la déconnexion:', e);
    }
  };

  const clearError = () => setError(null);

  return (
    <AuthContext.Provider
      value={{
        token,
        isLoading,
        isAuthenticated: !!token,
        login,
        register,
        logout,
        error,
        clearError,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// Hook personnalisé pour utiliser le contexte facilement
export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth doit être utilisé dans un AuthProvider');
  }
  return context;
}