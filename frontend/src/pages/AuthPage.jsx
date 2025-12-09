import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';

const AuthPage = () => {
  const { setToken } = useAuth();
  const navigate = useNavigate();
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    firstName: '',
    lastName: ''
  });
  const [errors, setErrors] = useState({});

  // Установка заголовка страницы
  useEffect(() => {
    document.title = 'Вход | Геймификация предприятий';
  }, []);

  // Предупреждение при попытке закрыть страницу
  useEffect(() => {
    const handleBeforeUnload = (e) => {
      e.preventDefault();
      e.returnValue = '';
      return '';
    };

    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, []);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
    if (errors[name]) {
      setErrors({ ...errors, [name]: '' });
    }
  };

  const validateForm = () => {
    const newErrors = {};
    if (!formData.email) {
      newErrors.email = 'Электронная почта обязательна';
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      newErrors.email = 'Некорректный адрес электронной почты';
    }
    if (!formData.password) {
      newErrors.password = 'Пароль обязателен';
    } else if (formData.password.length < 6) {
      newErrors.password = 'Пароль должен содержать не менее 6 символов';
    }
    if (!isLogin) {
      if (!formData.firstName.trim()) {
        newErrors.firstName = 'Имя обязательно';
      }
      if (!formData.lastName.trim()) {
        newErrors.lastName = 'Фамилия обязательна';
      }
      if (!formData.confirmPassword) newErrors.confirmPassword = 'Пожалуйста, подтвердите пароль';
      else if (formData.password !== formData.confirmPassword) {
        newErrors.confirmPassword = 'Пароли не совпадают';
      }
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;

    try {
      const endpoint = isLogin ? '/login' : '/register';
      const payload = isLogin
        ? { email: formData.email.trim(), password: formData.password }
        : {
            first_name: formData.firstName.trim(),
            last_name: formData.lastName.trim(),
            email: formData.email.trim(),
            password: formData.password
          };

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        // Для статуса 401 при входе показываем сообщение о неверных данных
        if (response.status === 401 && isLogin) {
          throw new Error('Неверный email или пароль. Попробуйте снова.');
        }
        
        let errorMessage = '';
        if (errorData.detail) {
          if (Array.isArray(errorData.detail)) {
            // Ошибки валидации Pydantic приходят как массив
            errorMessage = errorData.detail.map(err => err.msg || err.message || JSON.stringify(err)).join(', ');
          } else {
            // HTTPException возвращает строку
            errorMessage = errorData.detail;
          }
        } else if (errorData.message) {
          errorMessage = errorData.message;
        } else {
          errorMessage = `Ошибка HTTP! Статус: ${response.status}`;
        }
        
        throw new Error(errorMessage);
      }
      
      const data = await response.json();

      if (isLogin) {
        // При входе получаем токен
        const token = data.access_token || data.token;
        const user = data.user || { email: formData.email };

        if (!token) {
          throw new Error('Сервер не вернул токен авторизации');
        }

        setToken(token, user);
        navigate('/');
      } else {
        setErrors({ success: 'Пользователь успешно создан' });
        setTimeout(() => {
          setIsLogin(true);
          setFormData({ email: formData.email, password: '', confirmPassword: '', firstName: '', lastName: '' });
          setErrors({});
        }, 2100);
      }
    } catch (error) {
      console.error('Ошибка авторизации:', error);
      setErrors({ ...errors, submit: error.message || 'Не удалось выполнить операцию' });
    }
  };

  const toggleMode = () => {
    setIsLogin(!isLogin);
    setFormData({ email: '', password: '', confirmPassword: '', firstName: '', lastName: '' });
    setErrors({});
  };

  return (
    <div className="flex justify-center items-center min-h-screen bg-gradient-to-br from-indigo-500 via-purple-500 to-purple-600 p-5">
      <div className="bg-white p-8 rounded-xl shadow-2xl w-full max-w-md">
        <h2 className="text-center mb-6 text-2xl font-semibold text-gray-800">
          {isLogin ? 'Вход' : 'Регистрация'}
        </h2>
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label htmlFor="email" className="block mb-2 text-gray-700 font-medium">
              Электронная почта
            </label>
            <input
              type="email"
              id="email"
              name="email"
              value={formData.email}
              onChange={handleInputChange}
              className={`w-full px-3 py-3 border rounded-lg text-base transition-all focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent ${
                errors.email ? 'border-red-500' : 'border-gray-300'
              }`}
              placeholder="Введите вашу электронную почту"
            />
            {errors.email && (
              <span className="block text-red-500 text-sm mt-1">{errors.email}</span>
            )}
          </div>

          {!isLogin && (
            <>
              <div className="mb-4">
                <label htmlFor="firstName" className="block mb-2 text-gray-700 font-medium">
                  Имя
                </label>
                <input
                  type="text"
                  id="firstName"
                  name="firstName"
                  value={formData.firstName}
                  onChange={handleInputChange}
                  className={`w-full px-3 py-3 border rounded-lg text-base transition-all focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent ${
                    errors.firstName ? 'border-red-500' : 'border-gray-300'
                  }`}
                  placeholder="Введите ваше имя"
                />
                {errors.firstName && (
                  <span className="block text-red-500 text-sm mt-1">{errors.firstName}</span>
                )}
              </div>
              <div className="mb-4">
                <label htmlFor="lastName" className="block mb-2 text-gray-700 font-medium">
                  Фамилия
                </label>
                <input
                  type="text"
                  id="lastName"
                  name="lastName"
                  value={formData.lastName}
                  onChange={handleInputChange}
                  className={`w-full px-3 py-3 border rounded-lg text-base transition-all focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent ${
                    errors.lastName ? 'border-red-500' : 'border-gray-300'
                  }`}
                  placeholder="Введите вашу фамилию"
                />
                {errors.lastName && (
                  <span className="block text-red-500 text-sm mt-1">{errors.lastName}</span>
                )}
              </div>
            </>
          )}

          <div className="mb-4">
            <label htmlFor="password" className="block mb-2 text-gray-700 font-medium">
              Пароль
            </label>
            <input
              type="password"
              id="password"
              name="password"
              value={formData.password}
              onChange={handleInputChange}
              className={`w-full px-3 py-3 border rounded-lg text-base transition-all focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent ${
                errors.password ? 'border-red-500' : 'border-gray-300'
              }`}
              placeholder="Введите ваш пароль"
            />
            {errors.password && (
              <span className="block text-red-500 text-sm mt-1">{errors.password}</span>
            )}
          </div>

          {!isLogin && (
            <div className="mb-4">
              <label htmlFor="confirmPassword" className="block mb-2 text-gray-700 font-medium">
                Подтверждение пароля
              </label>
              <input
                type="password"
                id="confirmPassword"
                name="confirmPassword"
                value={formData.confirmPassword}
                onChange={handleInputChange}
                className={`w-full px-3 py-3 border rounded-lg text-base transition-all focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent ${
                  errors.confirmPassword ? 'border-red-500' : 'border-gray-300'
                }`}
                placeholder="Подтвердите ваш пароль"
              />
              {errors.confirmPassword && (
                <span className="block text-red-500 text-sm mt-1">{errors.confirmPassword}</span>
              )}
            </div>
          )}

          {errors.success && (
            <div className="text-center p-2 bg-green-50 border border-green-200 rounded-lg mb-4 text-green-600 text-sm">
              {errors.success}
            </div>
          )}
          {errors.submit && (
            <div className="text-center p-2 bg-red-50 border border-red-200 rounded-lg mb-4 text-red-600 text-sm">
              {errors.submit}
            </div>
          )}
          <button
            type="submit"
            className="w-full py-3 bg-gradient-to-r from-indigo-500 to-purple-600 text-white rounded-lg text-base font-medium cursor-pointer transition-opacity hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
          >
            {isLogin ? 'Войти' : 'Зарегистрироваться'}
          </button>
        </form>

        <p className="text-center mt-6 text-gray-600">
          {isLogin ? 'Нет аккаунта? ' : 'Уже есть аккаунт? '}
          <button
            type="button"
            onClick={toggleMode}
            className="bg-transparent border-none text-indigo-600 cursor-pointer font-semibold underline p-0 ml-1 hover:text-purple-600 transition-colors"
          >
            {isLogin ? 'Зарегистрироваться' : 'Войти'}
          </button>
        </p>
      </div>
    </div>
  );
};

export default AuthPage;