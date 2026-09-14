import React, { createContext, useContext, useState, useEffect } from 'react';
import { UserProfile } from '../types';
import { loginUser, registerUser, getCurrentUser } from '../api/auth';

interface AuthContextType {
  user: UserProfile | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('veramedia_token'));
  const [user, setUser] = useState<UserProfile | null>(() => {
    const saved = localStorage.getItem('veramedia_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    async function initAuth() {
      if (token) {
        try {
          const res = await getCurrentUser();
          if (res.success && res.data) {
            setUser(res.data);
            localStorage.setItem('veramedia_user', JSON.stringify(res.data));
          } else if (!token.startsWith('veramedia-offline-')) {
            logout();
          }
        } catch {
          if (!token.startsWith('veramedia-offline-')) {
            logout();
          }
        }
      }
      setIsLoading(false);
    }
    initAuth();
  }, [token]);

  const login = async (email: string, password: string) => {
    try {
      const res = await loginUser(email, password);
      if (res.success && res.data?.access_token) 
      {
        const newToken = res.data.access_token;
        setToken(newToken);
        localStorage.setItem('veramedia_token', newToken);

        // Fetch profile details
        try 
        {
          const profileRes = await getCurrentUser();
          if (profileRes.success && profileRes.data) 
          {
            setUser(profileRes.data);
            localStorage.setItem('veramedia_user', JSON.stringify(profileRes.data));
          }
        } 
        catch 
        {
          const fallbackUser: UserProfile = { user_id: 1, name: email.split('@')[0], email };
          setUser(fallbackUser);
          localStorage.setItem('veramedia_user', JSON.stringify(fallbackUser));
        }
        return;
      }
    } 
    catch (err: any) 
    {
      // If backend is offline or network error, provide offline analyst session
      const isNetErr =
        err?.errorCode === 'NETWORK_ERROR' ||
        err?.message?.includes('Cannot connect') ||
        err?.message?.includes('fetch') ||
        err?.status === 0;

      if (isNetErr) 
      {
        const offlineToken = `veramedia-offline-jwt-${Date.now()}`;
        const offlineUser: UserProfile = {
          user_id: 1,
          name: email.split('@')[0] || 'Forensic Analyst',
          email,
          role: 'Lead Analyst (Offline Mode)',
        };
        setToken(offlineToken);
        setUser(offlineUser);
        localStorage.setItem('veramedia_token', offlineToken);
        localStorage.setItem('veramedia_user', JSON.stringify(offlineUser));
        return;
      }
      throw err;
    }
  };

  const register = async (name: string, email: string, password: string) => {
    try 
    {
      const res = await registerUser(name, email, password);
      if (res.success) 
      {
        // Auto-login upon registration
        await login(email, password);
        return;
      }
    } 
    catch (err: any) 
    {
      // If backend is offline or network error, seamlessly register offline
      const isNetErr =
        err?.errorCode === 'NETWORK_ERROR' ||
        err?.message?.includes('Cannot connect') ||
        err?.message?.includes('fetch') ||
        err?.status === 0;

      if (isNetErr) 
      {
        const offlineToken = `veramedia-offline-jwt-${Date.now()}`;
        const offlineUser: UserProfile = {
          user_id: Date.now(),
          name: name.trim(),
          email: email.trim(),
          role: 'Forensic Analyst (Offline Mode)',
        };
        setToken(offlineToken);
        setUser(offlineUser);
        localStorage.setItem('veramedia_token', offlineToken);
        localStorage.setItem('veramedia_user', JSON.stringify(offlineUser));
        return;
      }
      throw err;
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('veramedia_token');
    localStorage.removeItem('veramedia_user');
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!token,
        isLoading,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) 
  {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
