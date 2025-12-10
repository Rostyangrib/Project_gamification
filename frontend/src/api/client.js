// src/api/client.js
import { useAuth } from '../context/AuthContext.jsx';

// Базовый URL (можно вынести в .env). По умолчанию — корень (бек без префикса).
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

// Хук для использования в компонентах
export const useApi = () => {
  const { token } = useAuth();

  const request = async (endpoint, options = {}) => {
    const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;

    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    };

    // ✅ Добавляем токен, если есть
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    try {
      const response = await fetch(url, config);

      // Обработка 401 — токен недействителен
      if (response.status === 401) {
        // Можно вызвать logout(), но пока просто пробросим ошибку
        throw new Error('Сессия истекла. Пожалуйста, войдите снова.');
      }

      const contentType = response.headers.get('content-type') || '';
      const isJson = contentType.includes('application/json');
      const data = isJson ? await response.json() : await response.text();

      if (!response.ok) {
        const message =
          (isJson && (data.detail || data.message)) ||
          (!isJson && data) ||
          `Ошибка ${response.status}`;
        throw new Error(message);
      }

      return data;
    } catch (error) {
      // Перехватываем сетевые ошибки
      if (error.name === 'TypeError') {
        throw new Error('Нет подключения к серверу');
      }
      throw error;
    }
  };

  return {
    get: (endpoint) => request(endpoint, { method: 'GET' }),
    post: (endpoint, body) => request(endpoint, { method: 'POST', body: JSON.stringify(body) }),
    put: (endpoint, body) => request(endpoint, { method: 'PUT', body: JSON.stringify(body) }),
    delete: (endpoint) => request(endpoint, { method: 'DELETE' })
  };
};