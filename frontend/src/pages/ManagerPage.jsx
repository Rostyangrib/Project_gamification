import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import { useApi } from '../api/client.js';

const ManagerPage = () => {
  const { isAuthenticated, user } = useAuth();
  const api = useApi();
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    title: '',
    start_date: '',
    end_date: ''
  });
  const [selectedUsers, setSelectedUsers] = useState([]);
  const [allUsers, setAllUsers] = useState([]);
  const [tasks, setTasks] = useState([{ title: '', user_ids: [] }]);
  const [loading, setLoading] = useState(false);
  const [loadingUsers, setLoadingUsers] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    document.title = 'Управление соревнованиями | Геймификация предприятий';
    const link = document.querySelector("link[rel~='icon']") || document.createElement('link');
    link.rel = 'icon';
    link.href = '/favicon-g.svg';
    document.head.appendChild(link);

    // Проверка авторизации и прав администратора
    if (!isAuthenticated) {
      navigate('/login');
      return;
    }

    if (user?.role !== 'admin') {
      navigate('/');
      return;
    }

    // Загрузка списка пользователей
    loadUsers();
  }, [isAuthenticated, user, navigate]);

  const loadUsers = async () => {
    try {
      setLoadingUsers(true);
      // Берём только обычных пользователей, которых можно добавить в соревнование
      const users = await api.get('/users/only');
      setAllUsers(users || []);
    } catch (err) {
      console.error('Ошибка загрузки пользователей:', err);
      setError('Не удалось загрузить список пользователей');
    } finally {
      setLoadingUsers(false);
    }
  };



  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    setError('');
  };

  const toggleUserSelection = (userId) => {
    setSelectedUsers(prev => {
      const newSelected = prev.includes(userId)
        ? prev.filter(id => id !== userId)
        : [...prev, userId];
      
      // Очищаем выбранных пользователей в задачах, если они больше не в списке участников
      setTasks(currentTasks => 
        currentTasks.map(task => ({
          ...task,
          user_ids: task.user_ids.filter(id => newSelected.includes(id))
        }))
      );
      
      return newSelected;
    });
  };

  const addTask = () => {
    setTasks(prev => [...prev, { title: '', user_ids: [] }]);
  };

  const removeTask = (index) => {
    setTasks(prev => prev.filter((_, i) => i !== index));
  };

  const updateTask = (index, field, value) => {
    setTasks(prev => {
      const updated = [...prev];
      updated[index] = { ...updated[index], [field]: value };
      return updated;
    });
  };

  const toggleTaskUser = (taskIndex, userId) => {
    setTasks(prev => {
      const updated = [...prev];
      const task = updated[taskIndex];
      if (task.user_ids.includes(userId)) {
        task.user_ids = task.user_ids.filter(id => id !== userId);
      } else {
        task.user_ids = [...task.user_ids, userId];
      }
      return updated;
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    // Валидация
    if (!formData.title.trim()) {
      setError('Введите название соревнования');
      return;
    }

    if (!formData.start_date) {
      setError('Выберите дату начала соревнования');
      return;
    }

    if (!formData.end_date) {
      setError('Выберите дедлайн соревнования');
      return;
    }

    const startDate = new Date(formData.start_date);
    const endDate = new Date(formData.end_date);
    const now = new Date();
    
    if (startDate < now) {
      setError('Дата начала должна быть в будущем или сегодня');
      return;
    }

    if (endDate <= startDate) {
      setError('Дедлайн должен быть позже даты начала');
      return;
    }

    if (selectedUsers.length === 0) {
      setError('Выберите хотя бы одного участника');
      return;
    }

    // Валидация задач
    const validTasks = tasks.filter(t => t.title.trim() && t.user_ids.length > 0);
    if (validTasks.length === 0) {
      setError('Добавьте хотя бы одну задачу с выбранными пользователями');
      return;
    }

    try {
      setLoading(true);

      // Создаем соревнование
      const competition = await api.post('/competitions', {
        title: formData.title.trim(),
        start_date: startDate.toISOString(),
        end_date: endDate.toISOString()
      });

      // Убеждаемся, что ID соревнования - число
      const competitionId = typeof competition.id === 'string' ? parseInt(competition.id) : competition.id;

      // Назначаем пользователей на соревнование
      const assignPromises = selectedUsers.map(userId =>
        api.put(`/users/${userId}/competition`, {
          competition_id: competitionId
        })
      );

      await Promise.all(assignPromises);

      // Создаем задачи для выбранных пользователей через /chat
      // Для каждой задачи передаем текст и ID выбранных пользователей
      const taskPromises = [];
      validTasks.forEach(task => {
        // Формируем сообщение для AI, которое создаст задачу
        const message = `Создай задачу "${task.title.trim()}"`;
        
        // Передаем message и user_ids для создания задач для всех выбранных пользователей
        taskPromises.push(
          api.post('/chat', { 
            message,
            user_ids: task.user_ids
          })
        );
      });

      await Promise.all(taskPromises);

      setSuccess('Соревнование и задачи успешно созданы!');
      
      // Очистка формы
      setFormData({ title: '', start_date: '', end_date: '' });
      setSelectedUsers([]);
      setTasks([{ title: '', user_ids: [] }]);

      // Автоматически скрыть сообщение успеха через 5 секунд
      setTimeout(() => setSuccess(''), 5000);
    } catch (err) {
      console.error('Ошибка создания соревнования:', err);
      setError(err.message || 'Не удалось создать соревнование');
    } finally {
      setLoading(false);
    }
  };

  if (!isAuthenticated || user?.role !== 'admin') {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-4 sm:p-6">
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl sm:text-4xl font-bold text-gray-800 dark:text-gray-100 mb-2">
            🏆 Управление соревнованиями
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Создайте новое соревнование и выберите участников
          </p>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 sm:p-8">
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Название соревнования */}
            <div>
              <label htmlFor="title" className="block mb-2 text-sm font-medium text-gray-700 dark:text-gray-300">
                Название соревнования *
              </label>
              <input
                type="text"
                id="title"
                name="title"
                value={formData.title}
                onChange={handleInputChange}
                className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                placeholder="Введите название соревнования"
                required
              />
            </div>

            {/* Дата начала соревнования */}
            <div>
              <label htmlFor="start_date" className="block mb-2 text-sm font-medium text-gray-700 dark:text-gray-300">
                Дата начала соревнования *
              </label>
              <input
                type="datetime-local"
                id="start_date"
                name="start_date"
                value={formData.start_date}
                onChange={handleInputChange}
                className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                required
              />
            </div>

            {/* Дедлайн соревнования */}
            <div>
              <label htmlFor="end_date" className="block mb-2 text-sm font-medium text-gray-700 dark:text-gray-300">
                Дедлайн соревнования *
              </label>
              <input
                type="datetime-local"
                id="end_date"
                name="end_date"
                value={formData.end_date}
                onChange={handleInputChange}
                min={formData.start_date || undefined}
                className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                required
              />
            </div>

            {/* Выбор участников */}
            <div>
              <label className="block mb-3 text-sm font-medium text-gray-700 dark:text-gray-300">
                Участники соревнования * ({selectedUsers.length} выбрано)
              </label>
              
              {loadingUsers ? (
                <div className="text-center py-8">
                  <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-indigo-500 border-t-transparent"></div>
                  <p className="mt-2 text-gray-600 dark:text-gray-400">Загрузка пользователей...</p>
                </div>
              ) : allUsers.length === 0 ? (
                <p className="text-gray-500 dark:text-gray-400 text-center py-4">
                  Нет доступных пользователей
                </p>
              ) : (
                <div className="border border-gray-300 dark:border-gray-600 rounded-lg p-4 max-h-96 overflow-y-auto bg-gray-50 dark:bg-gray-700/30">
                  <div className="space-y-2">
                    {allUsers.map((userItem) => (
                      <label
                        key={userItem.id}
                        className="flex items-center p-3 rounded-lg cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors"
                      >
                        <input
                          type="checkbox"
                          checked={selectedUsers.includes(userItem.id)}
                          onChange={() => toggleUserSelection(userItem.id)}
                          className="w-5 h-5 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500 focus:ring-2"
                        />
                        <div className="ml-3 flex-1">
                          <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                            {userItem.first_name} {userItem.last_name}
                          </span>
                          <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">
                            ({userItem.email})
                          </span>
                          <span className="ml-2 text-xs text-indigo-600 dark:text-indigo-400 font-semibold">
                            {userItem.total_points} баллов
                          </span>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Добавление задач */}
            {formData.title.trim() && selectedUsers.length > 0 && (
              <div>
                <div className="flex justify-between items-center mb-3">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    Задачи соревнования ({tasks.filter(t => t.title.trim() && t.user_ids.length > 0).length} добавлено)
                  </label>
                  <button
                    type="button"
                    onClick={addTask}
                    className="px-3 py-1.5 text-sm bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 rounded-lg hover:bg-indigo-200 dark:hover:bg-indigo-900/50 transition-colors flex items-center gap-1"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                    </svg>
                    Добавить задачу
                  </button>
                </div>
                
                <div className="space-y-4">
                  {tasks.map((task, index) => (
                    <div key={index} className="border border-gray-300 dark:border-gray-600 rounded-lg p-4 bg-gray-50 dark:bg-gray-700/30">
                      <div className="flex justify-between items-start mb-3">
                        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                          Задача #{index + 1}
                        </span>
                        {tasks.length > 1 && (
                          <button
                            type="button"
                            onClick={() => removeTask(index)}
                            className="text-red-500 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
                            title="Удалить задачу"
                          >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                          </button>
                        )}
                      </div>
                      
                      <div className="space-y-3">
                        <div>
                          <label className="block mb-1 text-xs font-medium text-gray-600 dark:text-gray-400">
                            Название задачи *
                          </label>
                          <input
                            type="text"
                            value={task.title}
                            onChange={(e) => updateTask(index, 'title', e.target.value)}
                            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                            placeholder="Введите название задачи"
                          />
                        </div>
                        
                        <div className="space-y-3">
                          <div>
                            <label className="block mb-1 text-xs font-medium text-gray-600 dark:text-gray-400">
                              Пользователи * ({task.user_ids.length} выбрано)
                            </label>
                            <div className="border border-gray-300 dark:border-gray-600 rounded-lg p-2 max-h-40 overflow-y-auto bg-white dark:bg-gray-700">
                              {selectedUsers.length === 0 ? (
                                <p className="text-xs text-gray-500 dark:text-gray-400 text-center py-2">
                                  Сначала выберите участников соревнования выше
                                </p>
                              ) : (
                                <div className="space-y-1">
                                  {allUsers
                                    .filter(userItem => selectedUsers.includes(userItem.id))
                                    .map((userItem) => (
                                      <label
                                        key={userItem.id}
                                        className="flex items-center p-2 rounded cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors"
                                      >
                                        <input
                                          type="checkbox"
                                          checked={task.user_ids.includes(userItem.id)}
                                          onChange={() => toggleTaskUser(index, userItem.id)}
                                          className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500 focus:ring-1"
                                        />
                                        <span className="ml-2 text-xs text-gray-900 dark:text-gray-100">
                                          {userItem.first_name} {userItem.last_name}
                                        </span>
                                      </label>
                                    ))}
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {formData.title.trim() && selectedUsers.length === 0 && (
              <div className="p-4 bg-yellow-50 dark:bg-yellow-900/30 border border-yellow-200 dark:border-yellow-800 rounded-lg">
                <p className="text-yellow-600 dark:text-yellow-400 text-sm">
                  Выберите участников соревнования выше, чтобы добавить задачи
                </p>
              </div>
            )}

            {/* Сообщения об ошибках и успехе */}
            {error && (
              <div className="p-4 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg">
                <p className="text-red-600 dark:text-red-400 text-sm">{error}</p>
              </div>
            )}

            {success && (
              <div className="p-4 bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 rounded-lg">
                <p className="text-green-600 dark:text-green-400 text-sm">{success}</p>
              </div>
            )}

            {/* Кнопка отправки */}
            <button
              type="submit"
              disabled={loading || loadingUsers}
              className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-600 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Создание...' : 'Создать соревнование'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default ManagerPage;

