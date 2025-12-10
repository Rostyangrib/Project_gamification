import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import { useApi } from '../api/client.js';

const ProfilePage = () => {
  const { isAuthenticated, user, updateUser } = useAuth();
  const api = useApi();
  const navigate = useNavigate();

  const [form, setForm] = useState({
    email: user?.email || '',
    password: '',
    confirmPassword: ''
  });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState('');

  useEffect(() => {
    document.title = 'Профиль | Геймификация предприятий';
    const link = document.querySelector("link[rel~='icon']") || document.createElement('link');
    link.rel = 'icon';
    link.href = '/favicon-g.svg';
    document.head.appendChild(link);

    if (!isAuthenticated) {
      navigate('/login');
    } else if (user?.email) {
      setForm((prev) => ({ ...prev, email: user.email }));
    }
  }, [isAuthenticated, user, navigate]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    setErrors((prev) => ({ ...prev, [name]: '' }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSuccess('');

    const nextErrors = {};
    if (!form.email) nextErrors.email = 'Email обязателен';
    if (form.password && form.password.length < 6) {
      nextErrors.password = 'Пароль должен быть не менее 6 символов';
    }
    if (form.password !== form.confirmPassword) {
      nextErrors.confirmPassword = 'Пароли не совпадают';
    }

    if (Object.keys(nextErrors).length) {
      setErrors(nextErrors);
      return;
    }

    try {
      setLoading(true);
      const payload = {};
      if (form.email && form.email !== user?.email) payload.email = form.email;
      if (form.password) payload.password = form.password;

      if (Object.keys(payload).length === 0) {
        setSuccess('Нет изменений для сохранения');
        return;
      }

      const updated = await api.put('/users/me', payload);
      updateUser(updated);
      setSuccess('Данные профиля обновлены');
      setForm((prev) => ({ ...prev, password: '', confirmPassword: '' }));
    } catch (err) {
      setErrors((prev) => ({ ...prev, submit: err.message || 'Ошибка обновления профиля' }));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex justify-center items-center min-h-screen bg-gray-50 dark:bg-gray-900 px-4 py-10">
      <div className="bg-white dark:bg-gray-800 p-8 rounded-xl shadow-lg w-full max-w-lg">
        <h2 className="text-2xl font-semibold mb-6 text-gray-800 dark:text-gray-100 text-center">
          Профиль
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block mb-1 text-sm font-medium text-gray-700 dark:text-gray-300">
              Электронная почта
            </label>
            <input
              type="email"
              name="email"
              value={form.email}
              onChange={handleChange}
              className={`w-full px-3 py-3 border rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent ${
                errors.email ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
              }`}
              placeholder="you@example.com"
            />
            {errors.email && <p className="text-red-500 text-sm mt-1">{errors.email}</p>}
          </div>

          <div>
            <label className="block mb-1 text-sm font-medium text-gray-700 dark:text-gray-300">
              Новый пароль (необязательно)
            </label>
            <input
              type="password"
              name="password"
              value={form.password}
              onChange={handleChange}
              className={`w-full px-3 py-3 border rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent ${
                errors.password ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
              }`}
              placeholder="Введите новый пароль"
            />
            {errors.password && <p className="text-red-500 text-sm mt-1">{errors.password}</p>}
          </div>

          <div>
            <label className="block mb-1 text-sm font-medium text-gray-700 dark:text-gray-300">
              Подтверждение пароля
            </label>
            <input
              type="password"
              name="confirmPassword"
              value={form.confirmPassword}
              onChange={handleChange}
              className={`w-full px-3 py-3 border rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent ${
                errors.confirmPassword ? 'border-red-500' : 'border-gray-300 dark:border-gray-600'
              }`}
              placeholder="Повторите пароль"
            />
            {errors.confirmPassword && (
              <p className="text-red-500 text-sm mt-1">{errors.confirmPassword}</p>
            )}
          </div>

          {errors.submit && (
            <div className="text-red-600 dark:text-red-400 text-sm bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded px-3 py-2">
              {errors.submit}
            </div>
          )}
          {success && (
            <div className="text-green-600 dark:text-green-400 text-sm bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 rounded px-3 py-2">
              {success}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {loading ? 'Сохранение...' : 'Сохранить изменения'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default ProfilePage;

