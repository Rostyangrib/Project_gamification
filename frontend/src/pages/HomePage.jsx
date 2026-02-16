import React, { useState, useMemo, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApi } from '../api/client.js';
import { useAuth } from '../context/AuthContext.jsx';

const getDaysInMonth = (year, month) => new Date(year, month + 1, 0).getDate();

const getFirstDayOfMonth = (year, month) => {
  const day = new Date(year, month, 1).getDay();
  return day === 0 ? 6 : day - 1;
};

const formatDateKey = (date) => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

const toGenitiveMonth = (name) => {
  if (name.endsWith('рь')) return name.slice(0, -1) + 'я';
  if (name.endsWith('ль')) return name.slice(0, -1) + 'я';
  if (name.endsWith('й')) return name.slice(0, -1) + 'я';
  if (name.endsWith('нь')) return name.slice(0, -1) + 'я';
  if (name.endsWith('т')) return name + 'а';
  return name;
};

const formatDateTime = (dateString) => {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
};

const getTimeRemaining = (endDate) => {
  if (!endDate) return '';
  const now = new Date();
  const end = new Date(endDate);
  const diff = end - now;

  if (diff < 0) return 'Соревнование завершено';

  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

  if (days > 0) return `Осталось: ${days} дн. ${hours} ч.`;
  if (hours > 0) return `Осталось: ${hours} ч. ${minutes} мин.`;
  return `Осталось: ${minutes} мин.`;
};

const getCompetitionStatus = (competition) => {
  if (!competition?.start_date || !competition?.end_date) {
    return {
      text: 'Без дат',
      color: 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
    };
  }

  const now = new Date();
  const startDate = new Date(competition.start_date);
  const endDate = new Date(competition.end_date);

  if (now < startDate) {
    return {
      text: 'Не началось',
      color: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
    };
  }

  if (now >= startDate && now <= endDate) {
    return {
      text: 'Идёт',
      color: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300'
    };
  }

  return {
    text: 'Завершено',
    color: 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300'
  };
};

const HomePage = () => {
  const api = useApi();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [competition, setCompetition] = useState(null);
  const [isLoadingCompetition, setIsLoadingCompetition] = useState(true);
  const [chatSuccess, setChatSuccess] = useState(null);
  const [competitions, setCompetitions] = useState([]);
  const [loadingCompetitions, setLoadingCompetitions] = useState(false);
  const [allUsers, setAllUsers] = useState([]);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const dashboardDataLoadedRef = useRef(false);
  const [userCompetitions, setUserCompetitions] = useState([]);
  const [selectedCompetitionId, setSelectedCompetitionId] = useState(null);
  const [competitionStats, setCompetitionStats] = useState(null);
  const [isLoadingCompetitionStats, setIsLoadingCompetitionStats] = useState(false);

  useEffect(() => {
    document.title = 'Панель геймификации';
    const link = document.querySelector("link[rel~='icon']") || document.createElement('link');
    link.rel = 'icon';
    link.href = '/favicon-g.svg';
    document.head.appendChild(link);
  }, []);

  const [currentDate, setCurrentDate] = useState(new Date());
  const [expandedDay, setExpandedDay] = useState(null);
  const [tasks, setTasks] = useState({});
  const [defaultStatusId, setDefaultStatusId] = useState(null);
  const [isLoadingTasks, setIsLoadingTasks] = useState(true);
  const inputRef = useRef(null);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState(null);
  const [completedStatusId, setCompletedStatusId] = useState(null);

  const mapTasksByDate = (taskList) => {
    const mapped = {};
    (taskList || []).forEach((task) => {
      const dateSource = task.due_date || task.created_at || new Date().toISOString();
      
      let date;
      if (typeof dateSource === 'string') {
        if (dateSource.includes('Z') || dateSource.match(/[+-]\d{2}:\d{2}$/)) {
          date = new Date(dateSource);
        } else {
          const dateMatch = dateSource.match(/(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?)?/);
          if (dateMatch) {
            const [, year, month, day, hours = '0', minutes = '0', seconds = '0'] = dateMatch;
            date = new Date(
              parseInt(year),
              parseInt(month) - 1,
              parseInt(day),
              parseInt(hours),
              parseInt(minutes),
              parseInt(seconds)
            );
          } else {
            date = new Date(dateSource);
          }
        }
      } else {
        date = new Date(dateSource);
      }
      
      const dateKey = formatDateKey(date);
      if (!mapped[dateKey]) mapped[dateKey] = [];
      mapped[dateKey].push(task);
    });
    return mapped;
  };

  useEffect(() => {
    const loadData = async () => {
      try {
        setIsLoadingTasks(true);
        const statuses = await api.get('/task-statuses');
        const defaultStatus = statuses.find(s => s.code === 'todo') || statuses[0];
        const completedStatus = statuses.find(s => s.code === 'done');
        setDefaultStatusId(defaultStatus?.id || null);
        setCompletedStatusId(completedStatus?.id || null);

        const tasksResp = await api.get('/tasks');
        setTasks(mapTasksByDate(tasksResp || []));
      } catch (err) {
        console.error('Ошибка загрузки задач:', err);
        setError(err.message || 'Не удалось загрузить задачи');
      } finally {
        setIsLoadingTasks(false);
      }
    };
    loadData();
  }, []);

  useEffect(() => {
    if (user?.role === 'admin' || user?.role === 'manager') {
      setIsLoadingCompetition(false);
      return;
    }
    
    const loadCompetition = async () => {
      try {
        setIsLoadingCompetition(true);
        setIsLoadingCompetitionStats(true);
        const userInfo = await api.get('/users/me');
        if (userInfo?.cur_comp) {
          try {
            const compInfo = await api.get(`/competitions/${userInfo.cur_comp}`);
            setCompetition(compInfo);
            setUserCompetitions([compInfo]);
            setSelectedCompetitionId(compInfo.id);

            try {
              const leaderboardRaw = await api.get(`/leaderboard/${userInfo.cur_comp}`);
              const usersArray = Array.isArray(leaderboardRaw) ? leaderboardRaw : [];
              const sortedUsers = usersArray
                .map((u) => ({
                  first_name: u.first_name || '',
                  last_name: u.last_name || '',
                  total_points: Number(u.total_points) || 0,
                }))
                .sort((a, b) => b.total_points - a.total_points);

              let userRank = null;
              let userPoints = null;

              const foundIndex = sortedUsers.findIndex(
                (u) =>
                  u.first_name === userInfo.first_name &&
                  u.last_name === userInfo.last_name
              );

              if (foundIndex !== -1) {
                userRank = foundIndex + 1;
                userPoints = sortedUsers[foundIndex].total_points;
              }

              setCompetitionStats({
                competitionId: userInfo.cur_comp,
                totalParticipants: sortedUsers.length,
                userRank,
                userPoints,
              });
            } catch (statsErr) {
              console.error('Ошибка загрузки статистики соревнования:', statsErr);
              setCompetitionStats(null);
            }
          } catch (err) {
            setCompetition({
              id: userInfo.cur_comp,
              title: 'Соревнование',
              end_date: null,
              start_date: null
            });
            setUserCompetitions([]);
            setSelectedCompetitionId(null);
            setCompetitionStats(null);
          }
        } else {
          setCompetition(null);
          setUserCompetitions([]);
          setSelectedCompetitionId(null);
          setCompetitionStats(null);
        }
      } catch (err) {
        console.error('Ошибка загрузки соревнования:', err);
        setCompetition(null);
        setUserCompetitions([]);
        setSelectedCompetitionId(null);
        setCompetitionStats(null);
      } finally {
        setIsLoadingCompetition(false);
        setIsLoadingCompetitionStats(false);
      }
    };
    loadCompetition();
  }, [user]);

  useEffect(() => {
    if (user?.role !== 'admin' && user?.role !== 'manager') {
      dashboardDataLoadedRef.current = false;
      return;
    }

    if (dashboardDataLoadedRef.current || loadingCompetitions || loadingUsers) {
      return;
    }

    dashboardDataLoadedRef.current = true;

    const loadDashboardData = async () => {
      try {
        setLoadingCompetitions(true);
        setLoadingUsers(true);
        
        const [comps, users] = await Promise.all([
          api.get('/competitions'),
          api.get('/users/only')
        ]);
        
        setCompetitions(comps || []);
        setAllUsers(users || []);
      } catch (err) {
        if (err.message && !err.message.includes('Нет подключения')) {
          console.error('Ошибка загрузки данных дашборда:', err);
        }
        setCompetitions([]);
        setAllUsers([]);
      } finally {
        setLoadingCompetitions(false);
        setLoadingUsers(false);
        dashboardDataLoadedRef.current = false;
      }
    };

    loadDashboardData();
  }, [user?.role]);

  const markTaskAsCompleted = async (taskId, estimatedPoints = 0) => {
    if (!completedStatusId) {
      setError('Статус "Выполнено" не найден');
      return;
    }

    try {
      // Проверка даты начала соревнования
      if (competition && competition.start_date) {
        const startDate = new Date(competition.start_date);
        const now = new Date();
        
        if (now < startDate) {
          const formattedDate = startDate.toLocaleString('ru-RU', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
          });
          setError(`Нельзя пометить задачу выполненной до начала соревнования. Соревнование начинается ${formattedDate}`);
          return;
        }
      }

      const allTasks = await api.get('/tasks');
      const task = allTasks.find(t => t.id === taskId);
      if (!task) {
        setError('Задача не найдена');
        return;
      }
      if (task.status_id === completedStatusId) {
        setError('Задача уже выполнена');
        return;
      }

      await api.put(`/tasks/${taskId}`, {
        status_id: completedStatusId,
        completed_at: new Date().toISOString(),
        title: task.title,
        description: task.description,
        ai_analysis_metadata: task.ai_analysis_metadata,
        estimated_points: task.estimated_points,
        due_date: task.due_date,
      });

      if (estimatedPoints > 0) {
        await api.post('/rewards', {
          type_id: "1",
          points_amount: estimatedPoints,
          reason: `Выполнена задача (ID: ${taskId})`,
        });
      }

      const tasksResp = await api.get('/tasks');
      setTasks(mapTasksByDate(tasksResp || []));
    } catch (err) {
      console.error('Ошибка завершения задачи:', err);
      let errorMessage = 'Не удалось завершить задачу';
      if (err && typeof err === 'object') {
        errorMessage = err.detail || err.message || JSON.stringify(err, null, 2);
      } else if (typeof err === 'string') {
        errorMessage = err;
      }
      setError(errorMessage);
    }
  };


  const removeTask = async (taskId) => {
    try {
      await api.delete(`/tasks/${taskId}`);
      const tasksResp = await api.get('/tasks');
      setTasks(mapTasksByDate(tasksResp || []));
    } catch (err) {
      console.error('Ошибка удаления задачи:', err);
      setError(err.message || 'Не удалось удалить задачу');
    }
  };

  const { year, month, days, startDay } = useMemo(() => {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    const daysInMonth = getDaysInMonth(year, month);
    const startDay = getFirstDayOfMonth(year, month);
    return { year, month, days: Array.from({ length: daysInMonth }, (_, i) => i + 1), startDay };
  }, [currentDate]);

  const getTasksForDay = (day) => {
    const dateKey = formatDateKey(new Date(year, month, day));
    return tasks[dateKey] || [];
  };

  const goToPreviousMonth = () => {
    setCurrentDate(new Date(year, month - 1, 1));
    setExpandedDay(null);
  };

  const goToNextMonth = () => {
    setCurrentDate(new Date(year, month + 1, 1));
    setExpandedDay(null);
  };

  const goToToday = () => {
    setCurrentDate(new Date());
    setExpandedDay(null);
  };

  const toggleDay = (day) => {
    const dateKey = formatDateKey(new Date(year, month, day));
    setExpandedDay(expandedDay === dateKey ? null : dateKey);
  };

  const isToday = (day) => {
    const today = new Date();
    return day === today.getDate() && month === today.getMonth() && year === today.getFullYear();
  };

  const isWeekend = (dayIndex) => {
    const dayOfWeek = (startDay + dayIndex) % 7;
    return dayOfWeek === 5 || dayOfWeek === 6;
  };

  if (user?.role === 'admin' || user?.role === 'manager') {
    const now = new Date();
    const activeCompetitions = competitions.filter(comp => {
      const start = new Date(comp.start_date);
      const end = new Date(comp.end_date);
      return now >= start && now <= end;
    });
    const upcomingCompetitions = competitions.filter(comp => {
      const start = new Date(comp.start_date);
      return now < start;
    });
    const completedCompetitions = competitions.filter(comp => {
      const end = new Date(comp.end_date);
      return now > end;
    });

    return (
      <div className="p-5 max-w-7xl mx-auto bg-gray-50 dark:bg-gray-900 min-h-screen">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-lg">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-600 dark:text-gray-400 text-sm">Всего соревнований</p>
                <p className="text-3xl font-bold text-gray-800 dark:text-gray-100 mt-1">
                  {loadingCompetitions ? '...' : competitions.length}
                </p>
              </div>
              <div className="text-4xl"></div>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-lg">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-600 dark:text-gray-400 text-sm">Активных</p>
                <p className="text-3xl font-bold text-green-600 dark:text-green-400 mt-1">
                  {loadingCompetitions ? '...' : activeCompetitions.length}
                </p>
              </div>
              <div className="text-4xl"></div>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-lg">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-600 dark:text-gray-400 text-sm">Участников</p>
                <p className="text-3xl font-bold text-blue-500 dark:text-blue-600 mt-1">
                  {loadingUsers ? '...' : allUsers.length}
                </p>
              </div>
              <div className="text-4xl"></div>
            </div>
          </div>
        </div>

        {/* Быстрые действия */}
        <div className={`grid grid-cols-1 ${user?.role === 'admin' ? 'md:grid-cols-2' : ''} gap-6 mb-8`}>
          <button
            onClick={() => navigate('/manager')}
            className="bg-gradient-to-r from-blue-500 to-blue-600 dark:from-blue-600 dark:to-blue-700 p-6 rounded-xl shadow-lg text-white hover:from-blue-600 hover:to-blue-700 dark:hover:from-blue-700 dark:hover:to-blue-800 transition-all transform hover:scale-105 w-full"
          >
            <div className="flex items-center gap-4">
              <div className="text-left">
                <h3 className="text-xl font-bold mb-1">Управление соревнованиями</h3>
                <p className="text-blue-100 text-sm">Создавайте и управляйте соревнованиями</p>
              </div>
            </div>
          </button>

          {user?.role === 'admin' && (
            <button
              onClick={() => navigate('/admin')}
              className="bg-gradient-to-r from-blue-500 to-blue-600 dark:from-blue-600 dark:to-blue-700 p-6 rounded-xl shadow-lg text-white hover:from-blue-600 hover:to-blue-700 dark:hover:from-blue-700 dark:hover:to-blue-800 transition-all transform hover:scale-105"
            >
              <div className="flex items-center gap-4">
                <div className="text-left">
                  <h3 className="text-xl font-bold mb-1">Админ-панель</h3>
                  <p className="text-blue-100 text-sm">Управление пользователями и настройками</p>
                </div>
              </div>
            </button>
          )}
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
          <h2 className="text-2xl font-bold text-gray-800 dark:text-gray-100 mb-6">
            Соревнования
          </h2>

          {loadingCompetitions ? (
            <div className="text-center py-8">
              <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent"></div>
            </div>
          ) : competitions.length === 0 ? (
            <p className="text-gray-500 dark:text-gray-400 text-center py-8">
              Нет созданных соревнований
            </p>
          ) : (
            <div className="space-y-4">
              {activeCompetitions.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold text-green-600 dark:text-green-400 mb-3">
                    Активные ({activeCompetitions.length})
                  </h3>
                  <div className="space-y-2">
                    {activeCompetitions.map((comp) => (
                      <div
                        key={comp.id}
                        className="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg"
                      >
                        <div className="flex justify-between items-start">
                          <div>
                            <h4 className="font-semibold text-gray-800 dark:text-gray-100">
                              {comp.title}
                            </h4>
                            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                              {formatDateTime(comp.start_date)} - {formatDateTime(comp.end_date)}
                            </p>
                          </div>
                          <button
                            onClick={() => navigate(`/manager?competitionId=${comp.id}`)}
                            className="px-3 py-1 bg-blue-500 hover:bg-blue-600 text-white rounded text-sm"
                          >
                            Управлять
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {upcomingCompetitions.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold text-blue-600 dark:text-blue-400 mb-3">
                    Предстоящие ({upcomingCompetitions.length})
                  </h3>
                  <div className="space-y-2">
                    {upcomingCompetitions.map((comp) => (
                      <div
                        key={comp.id}
                        className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg"
                      >
                        <div className="flex justify-between items-start">
                          <div>
                            <h4 className="font-semibold text-gray-800 dark:text-gray-100">
                              {comp.title}
                            </h4>
                            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                              Начало: {formatDateTime(comp.start_date)}
                            </p>
                          </div>
                          <button
                            onClick={() => navigate(`/manager?competitionId=${comp.id}`)}
                            className="px-3 py-1 bg-blue-500 hover:bg-blue-600 text-white rounded text-sm"
                          >
                            Управлять
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {completedCompetitions.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold text-gray-600 dark:text-gray-400 mb-3">
                    ⚫ Завершённые ({completedCompetitions.length})
                  </h3>
                  <div className="space-y-2">
                    {completedCompetitions.slice(0, 5).map((comp) => (
                      <div
                        key={comp.id}
                        className="p-4 bg-gray-50 dark:bg-gray-700/30 border border-gray-200 dark:border-gray-700 rounded-lg"
                      >
                        <div className="flex justify-between items-start">
                          <div>
                            <h4 className="font-semibold text-gray-800 dark:text-gray-100">
                              {comp.title}
                            </h4>
                            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                              {formatDateTime(comp.start_date)} - {formatDateTime(comp.end_date)}
                            </p>
                          </div>
                          <button
                            onClick={() => navigate(`/manager?competitionId=${comp.id}`)}
                            className="px-3 py-1 bg-gray-600 hover:bg-gray-700 text-white rounded text-sm"
                          >
                            Просмотр
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="p-5 max-w-7xl mx-auto bg-gray-50 dark:bg-gray-900 min-h-screen">
      <header className="mb-8 px-2.5 flex justify-between items-center">
        <h1 className="m-0 text-gray-800 dark:text-gray-100 font-bold text-2xl"></h1>
      </header>

      <div className="grid grid-cols-1 gap-8">
        {!isLoadingCompetition && competition && (
          <div className="bg-white dark:bg-gray-800 p-5 rounded-lg shadow-md border border-gray-200 dark:border-gray-700">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-stretch">
              <div className="flex flex-col justify-between">
                <div>
                  <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-100 mb-2">
                    Мои соревнования
                  </h2>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                    Выберите соревнование, чтобы посмотреть подробную информацию.
                  </p>
                  <div className="space-y-2">
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                      Соревнование
                    </label>
                    <select
                      value={selectedCompetitionId || ''}
                      onChange={(e) => {
                        const value = e.target.value ? Number(e.target.value) : null;
                        setSelectedCompetitionId(value);
                      }}
                      className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      disabled={userCompetitions.length <= 1}
                    >
                      {userCompetitions.length === 0 && (
                        <option value="">Нет доступных соревнований</option>
                      )}
                      {userCompetitions.map((comp) => (
                        <option key={comp.id} value={comp.id}>
                          {comp.title}
                        </option>
                      ))}
                    </select>
                    {userCompetitions.length <= 1 && (
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        Сейчас вы участвуете только в одном соревновании.
                      </p>
                    )}
                  </div>
                </div>
              </div>

              <div className="bg-gradient-to-r from-blue-500 to-blue-600 dark:from-blue-600 dark:to-blue-700 rounded-lg text-white p-5 flex flex-col justify-between">
                {(() => {
                  const currentComp =
                    userCompetitions.find((c) => c.id === selectedCompetitionId) || competition;
                  if (!currentComp) {
                    return (
                      <p className="text-sm text-blue-100">
                        Выберите соревнование слева, чтобы увидеть подробности.
                      </p>
                    );
                  }

                  const status = getCompetitionStatus(currentComp);
                  const statsAvailable =
                    competitionStats &&
                    competitionStats.competitionId === currentComp.id &&
                    competitionStats.userRank != null;

                  return (
                    <>
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <h3 className="text-2xl font-bold flex items-center gap-2">
                            {currentComp.title || 'Соревнование'}
                          </h3>
                          <span
                            className={`px-2 py-1 rounded-full text-xs font-semibold ${status.color}`}
                          >
                            {status.text}
                          </span>
                        </div>

                        <div className="space-y-1 text-sm">
                          {currentComp.start_date && (
                            <p className="text-blue-100">
                              <span className="font-semibold">Начало:</span>{' '}
                              {formatDateTime(currentComp.start_date)}
                            </p>
                          )}
                          {currentComp.end_date ? (
                            <>
                              <p className="text-blue-100">
                                <span className="font-semibold">Дедлайн:</span>{' '}
                                {formatDateTime(currentComp.end_date)}
                              </p>
                              <p className="text-blue-100 font-medium">
                                {getTimeRemaining(currentComp.end_date)}
                              </p>
                            </>
                          ) : (
                            <p className="text-blue-100">
                              Информация о дедлайне недоступна
                            </p>
                          )}
                        </div>

                        <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm">
                          <div className="bg-white/10 rounded-lg p-3">
                            <p className="text-blue-100 text-xs">Мои баллы</p>
                            {isLoadingCompetitionStats ? (
                              <p className="text-lg font-semibold">...</p>
                            ) : (
                              <p className="text-lg font-semibold">
                                {statsAvailable ? competitionStats.userPoints : '—'}
                              </p>
                            )}
                          </div>
                          <div className="bg-white/10 rounded-lg p-3">
                            <p className="text-blue-100 text-xs">Моё место</p>
                            {isLoadingCompetitionStats ? (
                              <p className="text-lg font-semibold">...</p>
                            ) : statsAvailable ? (
                              <p className="text-lg font-semibold">
                                {competitionStats.userRank}{' '}
                                <span className="text-xs text-blue-100">
                                  из {competitionStats.totalParticipants}
                                </span>
                              </p>
                            ) : (
                              <p className="text-lg font-semibold">—</p>
                            )}
                          </div>
                          <div className="bg-white/10 rounded-lg p-3">
                            <p className="text-blue-100 text-xs">Участников</p>
                            {isLoadingCompetitionStats ? (
                              <p className="text-lg font-semibold">...</p>
                            ) : competitionStats &&
                              competitionStats.competitionId === currentComp.id ? (
                              <p className="text-lg font-semibold">
                                {competitionStats.totalParticipants}
                              </p>
                            ) : (
                              <p className="text-lg font-semibold">—</p>
                            )}
                          </div>
                        </div>
                      </div>

                      <div className="mt-4">
                        <button
                          onClick={() => navigate('/leaderboards')}
                          className="inline-flex items-center px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm font-medium text-white transition-colors"
                        >
                          Открыть полный рейтинг
                        </button>
                      </div>
                    </>
                  );
                })()}
              </div>
            </div>
          </div>
        )}

        {!isLoadingCompetition && !competition && (
          <div className="bg-white dark:bg-gray-800 p-5 rounded-lg shadow-md border border-gray-200 dark:border-gray-700">
            <p className="text-gray-600 dark:text-gray-400 text-center">
              Вы не участвуете в соревновании
            </p>
          </div>
        )}

        <div className="bg-white dark:bg-gray-800 p-5 rounded-lg shadow-md">
          <div className="flex justify-between items-center mb-5">
            <h2 className="m-0 text-gray-800 dark:text-gray-100 font-semibold text-xl">
               {new Date(year, month).toLocaleString('ru-RU', { month: 'long', year: 'numeric' })}
            </h2>
            <div className="flex gap-2">
              <button
                onClick={goToToday}
                className="px-3 py-1.5 rounded cursor-pointer text-sm border border-blue-500 text-blue-500 dark:text-blue-400 bg-white dark:bg-gray-700 hover:bg-blue-50 dark:hover:bg-gray-600 transition-colors"
              >
                Сегодня
              </button>
              <button
                onClick={goToPreviousMonth}
                className="px-2.5 py-1.5 rounded cursor-pointer text-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors text-gray-900 dark:text-gray-100"
              >
                ‹
              </button>
              <button
                onClick={goToNextMonth}
                className="px-2.5 py-1.5 rounded cursor-pointer text-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors text-gray-900 dark:text-gray-100"
              >
                ›
              </button>
            </div>
          </div>

          <div className="grid grid-cols-7 text-center font-semibold mb-0 bg-gray-600 dark:bg-gray-700 text-white">
            {['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'].map(day => (
              <div
                key={day}
                className="py-2 px-1"
              >
                {day}
              </div>
            ))}
          </div>

          <div className="border border-gray-300 dark:border-gray-600 overflow-hidden">
            <div className="grid grid-cols-7">
              {Array.from({ length: startDay }).map((_, i) => {
                const colIndex = i % 7;
                const isLastCol = colIndex === 6;
                const totalCells = startDay + days.length;
                const rowIndex = Math.floor(i / 7);
                const totalRows = Math.ceil(totalCells / 7);
                const isLastRow = rowIndex === totalRows - 1;
                return (
                  <div 
                    key={`empty-${i}`} 
                    className={`h-[120px] bg-gray-50 dark:bg-gray-800 ${!isLastCol ? 'border-r border-gray-300 dark:border-gray-600' : ''} ${!isLastRow ? 'border-b border-gray-300 dark:border-gray-600' : ''}`}
                  ></div>
                );
              })}

              {days.map((day, dayIdx) => {
                const dayIndex = day - 1;
                const dateKey = formatDateKey(new Date(year, month, day));
                const dayTasks = getTasksForDay(day);
                const isExpanded = expandedDay === dateKey;
                const today = isToday(day);
                const weekend = isWeekend(dayIndex);
                const totalCells = startDay + days.length;
                const cellIndex = startDay + dayIdx;
                const colIndex = cellIndex % 7;
                const rowIndex = Math.floor(cellIndex / 7);
                const totalRows = Math.ceil(totalCells / 7);
                const isLastCol = colIndex === 6;
                const isLastRow = rowIndex === totalRows - 1;

                return (
                  <div
                    key={day}
                    onClick={() => dayTasks.length > 0 && toggleDay(day)}
                    className={`
                      min-h-[120px] transition-colors flex flex-col
                      ${!isLastCol ? 'border-r border-gray-300 dark:border-gray-600' : ''}
                      ${!isLastRow ? 'border-b border-gray-300 dark:border-gray-600' : ''}
                      ${today ? 'bg-blue-100 dark:bg-blue-900/40' : 'bg-gray-50 dark:bg-gray-800'}
                      ${isExpanded ? 'bg-gray-100 dark:bg-gray-700' : ''}
                      ${dayTasks.length > 0 ? 'cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700' : ''}
                    `.trim()}
                  >
                  <div
                    className={`
                      p-2 text-right text-sm
                      ${today ? 'font-bold' : ''}
                      ${weekend ? 'text-green-600 dark:text-green-400' : 'text-gray-900 dark:text-gray-100'}
                    `.trim()}
                  >
                    {today ? (
                      <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-blue-500 dark:bg-blue-600 text-white">
                        {day}
                      </span>
                    ) : (
                      <span>{day}</span>
                    )}
                  </div>

                  <div className="px-2 pb-2 text-sm flex-1">
                    {dayTasks.length > 0 ? (
                      <div>
                        {dayTasks.map((task, i) => (
                          <span
                            key={task.id || i}
                            className="bg-cyan-50 dark:bg-cyan-900/50 text-cyan-900 dark:text-cyan-100 px-2 py-1 rounded-full text-xs inline-block max-w-full break-words m-0.5"
                          >
                            {task.title.length > 15 ? task.title.slice(0, 15) + '…' : task.title}
                            {task.estimated_points && (
                              <span className="ml-1 text-blue-500 dark:text-blue-600 font-semibold">
                                ({task.estimated_points})
                              </span>
                            )}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <p className="text-gray-500 dark:text-gray-400 text-xs m-1">Нет задач</p>
                    )}
                  </div>

                  {dayTasks.length > 0 && !isExpanded && (
                    <div className="text-center text-xs text-gray-600 dark:text-gray-400 border-t border-dashed border-gray-200 dark:border-gray-700 pt-1 mt-auto">
                      Кликните для просмотра
                    </div>
                  )}

                  {isExpanded && dayTasks.length > 0 && (
                    <div className="p-2 border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 rounded-b-md">
                      <div className="text-sm text-gray-800 dark:text-gray-100 font-bold mb-2.5 text-center">
                        Задачи на {day} {toGenitiveMonth(new Date(year, month).toLocaleString('ru-RU', { month: 'long' }))}:
                      </div>
                      <ul className="list-none p-0 m-0 max-h-48 overflow-y-auto overflow-x-hidden">
                        {dayTasks.map((task, idx) => (
                          <li
                            key={task.id || idx}
                            className={`flex flex-col p-2.5 bg-blue-50 dark:bg-blue-900/30 rounded mb-2 
                              border-l-4 
                              transition-colors duration-300 ease-in-out
                              ${task.status_id === completedStatusId ? 'border-green-500 dark:border-green-400' : 'border-blue-500 dark:border-blue-400'}`}
                          >
                            <div className="break-words mb-2">
                              <span className="text-gray-900 dark:text-gray-100 break-words">{task.title}</span>
                              {task.estimated_points && (
                                <span className="ml-2 text-blue-500 dark:text-blue-600 font-semibold text-sm">
                                  {task.estimated_points}
                                </span>
                              )}
                            </div>

                            <div className="flex items-center gap-2 mt-auto">
                              {task.status_id !== completedStatusId ? (
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    if (task.id) {
                                      markTaskAsCompleted(task.id, task.estimated_points || 10);
                                    }
                                  }}
                                  className="text-green-600 dark:text-green-400 hover:text-green-800 dark:hover:text-green-300 transition-colors"
                                  title="Отметить как выполненную"
                                >
                                  ✓
                                </button>
                              ) : (
                                <span
                                  className="text-green-500 dark:text-green-400 opacity-70"
                                  title="Задача уже выполнена"
                                >
                                  ✓
                                </span>
                              )}

                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  if (task.id) {
                                    removeTask(task.id);
                                  }
                                }}
                                className="text-red-500 dark:text-red-400 cursor-pointer text-xl leading-none hover:text-red-700 dark:hover:text-red-300 transition-colors"
                                title="Удалить задачу"
                              >
                                ×
                              </button>
                            </div>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              );
            })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HomePage;
