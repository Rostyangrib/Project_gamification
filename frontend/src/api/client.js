import { useAuth } from '../context/AuthContext.jsx';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

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

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    try {
      const response = await fetch(url, config);

      if (response.status === 401) {
        throw new Error('Сессия истекла. Пожалуйста, войдите снова.');
      }

      const contentType = response.headers.get('content-type') || '';
      const isJson = contentType.includes('application/json');

      if (response.status === 204) {
        return null;
      }

      const rawText = await response.text();
      const data = isJson && rawText ? JSON.parse(rawText) : rawText;

      if (!response.ok) {
        const message =
          (isJson && (data.detail || data.message)) ||
          (!isJson && data) ||
          `Ошибка ${response.status}`;
        throw new Error(message);
      }

      return data;
    } catch (error) {
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