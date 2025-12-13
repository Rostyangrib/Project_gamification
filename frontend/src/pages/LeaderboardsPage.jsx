import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApi } from '../api/client.js';
import { useAuth } from '../context/AuthContext.jsx';

const LeaderboardsPage = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [competitionId, setCompetitionId] = useState(null);
  const api = useApi();
  const { user, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    // Проверка доступа: страница доступна только для обычных пользователей
    if (!isAuthenticated) {
      navigate('/login');
      return;
    }

    if (user?.role !== 'user') {
      navigate('/');
      return;
    }

    document.title = 'Список лидеров | Геймификация предприятий';
    const link = document.querySelector("link[rel~='icon']") || document.createElement('link');
    link.rel = 'icon';
    link.href = '/favicon-trophy.svg';
    document.head.appendChild(link);

    const fetchLeaderboard = async () => {
      try {
        setLoading(true);
        setError(null);

        // Определяем competition_id для текущего пользователя.
        // 1) Пробуем взять из контекста (после логина фронт там хранит пользователя)
        // 2) Пробуем получить свежий /users/me
        // 3) Фоллбек — 1 (чтобы страница не падала)
        let resolvedCompId = user?.cur_comp ?? null;
        try {
          const me = await api.get('/users/me');
          if (me?.cur_comp != null) {
            resolvedCompId = me.cur_comp;
          }
        } catch (meErr) {
          console.warn('Не удалось получить /users/me:', meErr);
        }
        if (resolvedCompId == null) {
          resolvedCompId = 1;
        }
        setCompetitionId(resolvedCompId);

        const data = await api.get(`/leaderboard/${resolvedCompId}`);

        const usersArray = Array.isArray(data) ? data : [];
        const sortedUsers = usersArray
          .map((u) => ({
            first_name: u.first_name || '',
            last_name: u.last_name || '',
            total_points: Number(u.total_points) || 0,
          }))
          .sort((a, b) => b.total_points - a.total_points);

        setUsers(sortedUsers);
      } catch (err) {
        console.error('Ошибка загрузки лидеров:', err);
        setError(err.message || 'Не удалось загрузить лидеров');
      } finally {
        setLoading(false);
      }
    };

    fetchLeaderboard();
  }, [isAuthenticated, user?.role, navigate]);

  const getRankIcon = (rank) => {
    if (rank === 1) {
      return (
        <div className="flex items-center justify-center w-8 h-8 rounded-full bg-gradient-to-br from-yellow-400 to-yellow-600 dark:from-yellow-500 dark:to-yellow-700 shadow-md">
          <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
          </svg>
        </div>
      );
    }
    if (rank === 2) {
      return (
        <div className="flex items-center justify-center w-8 h-8 rounded-full bg-gradient-to-br from-gray-300 to-gray-500 dark:from-gray-500 dark:to-gray-700 shadow-md">
          <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
          </svg>
        </div>
      );
    }
    if (rank === 3) {
      return (
        <div className="flex items-center justify-center w-8 h-8 rounded-full bg-gradient-to-br from-orange-400 to-orange-600 dark:from-orange-500 dark:to-orange-700 shadow-md">
          <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
          </svg>
        </div>
      );
    }
    return (
      <span className="text-base font-semibold text-gray-700 dark:text-gray-300">
        {rank}
      </span>
    );
  };

  const getRowStyle = (rank) => {
    if (rank === 1) {
      return 'bg-yellow-50/50 dark:bg-yellow-900/20 border-l-2 border-yellow-400 dark:border-yellow-600';
    }
    if (rank === 2) {
      return 'bg-gray-50/50 dark:bg-gray-700/30 border-l-2 border-gray-400 dark:border-gray-600';
    }
    if (rank === 3) {
      return 'bg-orange-50/50 dark:bg-orange-900/20 border-l-2 border-orange-400 dark:border-orange-600';
    }
    return 'hover:bg-gray-50 dark:hover:bg-gray-700/30';
  };

  // Проверка доступа перед рендерингом
  if (!isAuthenticated || user?.role !== 'user') {
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-purple-50 to-pink-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900 p-4 sm:p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8 text-center">
          <h1 className="text-4xl sm:text-5xl font-bold bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 dark:from-indigo-400 dark:via-purple-400 dark:to-pink-400 bg-clip-text text-transparent mb-2">
            🏆 Список лидеров
          </h1>
          <p className="text-gray-600 dark:text-gray-400 text-sm sm:text-base">
            Рейтинг участников по набранным очкам
          </p>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl dark:shadow-2xl overflow-hidden border border-gray-200 dark:border-gray-700">
          {loading ? (
            <div className="text-center py-16">
              <div className="inline-block h-12 w-12 animate-spin rounded-full border-4 border-indigo-500 border-t-transparent dark:border-indigo-400"></div>
              <p className="mt-4 text-gray-600 dark:text-gray-300 font-medium">Загрузка лидеров...</p>
            </div>
          ) : error ? (
            <div className="text-center py-16">
              <div className="mb-4 inline-flex items-center justify-center w-16 h-16 rounded-full bg-red-100 dark:bg-red-900/30">
                <svg className="h-8 w-8 text-red-500 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <p className="text-red-500 dark:text-red-400 font-medium">{error}</p>
            </div>
          ) : users.length === 0 ? (
            <div className="text-center py-16">
              <div className="mb-4 inline-flex items-center justify-center w-16 h-16 rounded-full bg-gray-100 dark:bg-gray-700">
                <svg className="h-8 w-8 text-gray-400 dark:text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <p className="text-gray-500 dark:text-gray-400 font-medium">Нет данных</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-700/50">
                  <tr>
                    <th scope="col" className="px-4 sm:px-6 py-4 text-left text-xs font-semibold text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      Место
                    </th>
                    <th scope="col" className="px-4 sm:px-6 py-4 text-left text-xs font-semibold text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      Участник
                    </th>
                    <th scope="col" className="px-4 sm:px-6 py-4 text-right text-xs font-semibold text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      Очки
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                  {users.map((user, index) => {
                    const rank = index + 1;
                    return (
                      <tr
                        key={rank}
                        className={`transition-colors duration-150 ${getRowStyle(rank)}`}
                      >
                        <td className="px-4 sm:px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            {getRankIcon(rank)}
                          </div>
                        </td>
                        <td className="px-4 sm:px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center space-x-2">
                            <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                              {user.first_name} {user.last_name}
                            </span>
                            {rank === 1 && (
                              <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-yellow-200 dark:bg-yellow-800 text-yellow-800 dark:text-yellow-200">
                                Чемпион
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="px-4 sm:px-6 py-4 whitespace-nowrap text-right">
                          <span className="inline-flex items-center px-3 py-1 text-sm font-semibold rounded-full bg-indigo-100 text-indigo-800 dark:bg-indigo-900/50 dark:text-indigo-200">
                            {user.total_points}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default LeaderboardsPage;