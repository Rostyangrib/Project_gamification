// src/context/AuthContext.jsx
import { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [authState, setAuthState] = useState(() => {
    // Инициализация из localStorage
    const token = localStorage.getItem('auth_token');
    const user = localStorage.getItem('auth_user');
    return {
      token,
      user: user ? JSON.parse(user) : null,
      isAuthenticated: !!token
    };
  });

  // Установка токена после входа/регистрации
  const setToken = (token, user = null) => {
    localStorage.setItem('auth_token', token);
    if (user) {
      localStorage.setItem('auth_user', JSON.stringify(user));
    }
    setAuthState({
      token,
      user: user || authState.user,
      isAuthenticated: true
    });
  };

  // Обновление данных пользователя в состоянии и localStorage
  const updateUser = (nextUser) => {
    if (!nextUser) return;
    const mergedUser = { ...authState.user, ...nextUser };
    localStorage.setItem('auth_user', JSON.stringify(mergedUser));
    setAuthState((prev) => ({
      ...prev,
      user: mergedUser,
      isAuthenticated: !!prev.token
    }));
  };

  // Выход
  const logout = () => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_user');
    setAuthState({
      token: null,
      user: null,
      isAuthenticated: false
    });
  };

  // Загрузка актуальных данных пользователя при перезагрузке страницы
  useEffect(() => {
    const loadUserData = async () => {
      const token = authState.token;
      if (!token) return;

      try {
        const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';
        const response = await fetch(`${API_BASE_URL}/users/me`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          }
        });

        if (response.ok) {
          const userData = await response.json();
          // Используем функциональное обновление состояния
          setAuthState((prev) => {
            const mergedUser = { ...prev.user, ...userData };
            localStorage.setItem('auth_user', JSON.stringify(mergedUser));
            return {
              ...prev,
              user: mergedUser
            };
          });
        } else if (response.status === 401) {
          // Токен недействителен - выходим
          localStorage.removeItem('auth_token');
          localStorage.removeItem('auth_user');
          setAuthState({
            token: null,
            user: null,
            isAuthenticated: false
          });
        }
      } catch (error) {
        console.error('Ошибка загрузки данных пользователя:', error);
        // Не выходим при ошибке сети, просто используем данные из localStorage
      }
    };

    loadUserData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authState.token]);

  return (
    <AuthContext.Provider value={{ ...authState, setToken, logout, updateUser }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};