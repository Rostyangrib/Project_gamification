// src/pages/HomePage.jsx
import React, { useState, useMemo, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom'; // ✅ добавлено
import { useApi } from '../api/client.js';
import { useAuth } from '../context/AuthContext.jsx'; // ✅ добавлено

// --- ВСЕ ХЕЛПЕРЫ ОСТАЮТСЯ БЕЗ ИЗМЕНЕНИЙ ---
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

// --- НОВЫЕ ХЕЛПЕРЫ ---
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

const HomePage = () => {
  const api = useApi();
  const { user } = useAuth(); // ✅
  const navigate = useNavigate(); // ✅

  // --- НОВОЕ СОСТОЯНИЕ ---
  const [competition, setCompetition] = useState(null);
  const [isLoadingCompetition, setIsLoadingCompetition] = useState(true);
  const [chatSuccess, setChatSuccess] = useState(null); // ✅

  // --- УСТАНОВКА TITLE И FAVICON ---
  useEffect(() => {
    document.title = 'Gamification Dashboard';
    const link = document.querySelector("link[rel~='icon']") || document.createElement('link');
    link.rel = 'icon';
    link.href = '/favicon-g.svg';
    document.head.appendChild(link);
  }, []);

  // --- СУЩЕСТВУЮЩИЕ СОСТОЯНИЯ (БЕЗ ИЗМЕНЕНИЙ) ---
  const [currentDate, setCurrentDate] = useState(new Date());
  const [expandedDay, setExpandedDay] = useState(null);
  const [tasks, setTasks] = useState({});
  const [defaultStatusId, setDefaultStatusId] = useState(null);
  const [isLoadingTasks, setIsLoadingTasks] = useState(true);
  const inputRef = useRef(null);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState(null);
  const [completedStatusId, setCompletedStatusId] = useState(null);

  // --- СУЩЕСТВУЮЩИЙ ХЕЛПЕР ---
  const mapTasksByDate = (taskList) => {
    const mapped = {};
    (taskList || []).forEach((task) => {
      const dateSource = task.due_date || task.created_at || new Date().toISOString();
      
      // Парсим дату правильно, учитывая разные форматы (с timezone и без)
      let date;
      if (typeof dateSource === 'string') {
        // Если строка содержит timezone (Z или +HH:MM), парсим как есть
        if (dateSource.includes('Z') || dateSource.match(/[+-]\d{2}:\d{2}$/)) {
          date = new Date(dateSource);
        } else {
          // Если нет timezone, интерпретируем как локальное время
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

  // --- СУЩЕСТВУЮЩИЙ ЭФФЕКТ ЗАГРУЗКИ ЗАДАЧ + СТАТУСОВ ---
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

  // --- НОВЫЙ ЭФФЕКТ: ЗАГРУЗКА СОРЕВНОВАНИЯ ---
  useEffect(() => {
    const loadCompetition = async () => {
      try {
        setIsLoadingCompetition(true);
        const userInfo = await api.get('/users/me');
        if (userInfo?.cur_comp) {
          try {
            const compInfo = await api.get(`/competitions/${userInfo.cur_comp}`);
            setCompetition(compInfo);
          } catch (err) {
            // Fallback: соревнование существует, но детали недоступны
            setCompetition({
              id: userInfo.cur_comp,
              title: 'Соревнование',
              end_date: null,
              start_date: null
            });
          }
        } else {
          setCompetition(null);
        }
      } catch (err) {
        console.error('Ошибка загрузки соревнования:', err);
        setCompetition(null);
      } finally {
        setIsLoadingCompetition(false);
      }
    };
    loadCompetition();
  }, []);

  // --- СУЩЕСТВУЮЩИЕ ФУНКЦИИ (БЕЗ ИЗМЕНЕНИЙ) ---
  const markTaskAsCompleted = async (taskId, estimatedPoints = 0) => {
    if (!completedStatusId) {
      setError('Статус "Выполнено" не найден');
      return;
    }

    try {
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

  // --- ВСЁ, ЧТО СВЯЗАНО С КАЛЕНДАРЕМ (БЕЗ ИЗМЕНЕНИЙ) ---
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

  // --- RENDER ---
  return (
    <div className="p-5 max-w-7xl mx-auto bg-gray-50 dark:bg-gray-900 min-h-screen">
      <header className="mb-8 px-2.5 flex justify-between items-center">
        <h1 className="m-0 text-gray-800 dark:text-gray-100 font-bold text-2xl">🎯 Gamification Dashboard</h1>
        {/* ✅ КНОПКА ДЛЯ АДМИНА */}
        {user?.role === 'admin' && (
          <button
            onClick={() => navigate('/manager')}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-600 text-white rounded-lg font-medium transition-colors flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
            Управление соревнованиями
          </button>
        )}
      </header>

      <div className="grid grid-cols-1 gap-8">
        {/* ✅ ПЛАШКА С СОРЕВНОВАНИЕМ */}
        {!isLoadingCompetition && competition && (
          <div className="bg-gradient-to-r from-indigo-500 to-purple-600 dark:from-indigo-600 dark:to-purple-700 p-6 rounded-lg shadow-lg text-white">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <h2 className="text-2xl font-bold mb-2 flex items-center gap-2">
                  🏆 {competition.title || 'Соревнование'}
                </h2>
                {competition.end_date ? (
                  <div className="space-y-1">
                    <p className="text-indigo-100 text-sm">
                      <span className="font-semibold">Дедлайн:</span> {formatDateTime(competition.end_date)}
                    </p>
                    <p className="text-indigo-100 text-sm font-medium">
                      {getTimeRemaining(competition.end_date)}
                    </p>
                  </div>
                ) : (
                  <p className="text-indigo-100 text-sm">
                    Информация о дедлайне недоступна
                  </p>
                )}
                {competition.start_date && (
                  <p className="text-indigo-100 text-sm mt-2">
                    <span className="font-semibold">Начало:</span> {formatDateTime(competition.start_date)}
                  </p>
                )}
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

        {/* ✅ КАЛЕНДАРЬ (БЕЗ ИЗМЕНЕНИЙ) */}
        <div className="bg-white dark:bg-gray-800 p-5 rounded-lg shadow-md">
          <div className="flex justify-between items-center mb-5">
            <h2 className="m-0 text-gray-800 dark:text-gray-100 font-semibold text-xl">
              📅 {new Date(year, month).toLocaleString('ru-RU', { month: 'long', year: 'numeric' })}
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

          <div className="grid grid-cols-7 text-center font-semibold mb-2 text-gray-800 dark:text-gray-200">
            {['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'].map(day => (
              <div
                key={day}
                className={day === 'Сб' || day === 'Вс' ? 'text-red-500 dark:text-red-400' : ''}
              >
                {day}
              </div>
            ))}
          </div>

          <div className="grid grid-cols-7 gap-1">
            {Array.from({ length: startDay }).map((_, i) => (
              <div key={`empty-${i}`} className="h-[120px]"></div>
            ))}

            {days.map(day => {
              const dayIndex = day - 1;
              const dateKey = formatDateKey(new Date(year, month, day));
              const dayTasks = getTasksForDay(day);
              const isExpanded = expandedDay === dateKey;
              const today = isToday(day);
              const weekend = isWeekend(dayIndex);

              return (
                <div
                  key={day}
                  onClick={() => dayTasks.length > 0 && toggleDay(day)}
                  className={`
                    border border-gray-200 dark:border-gray-700 rounded-md min-h-[120px] transition-colors flex flex-col
                    ${today ? 'bg-blue-50 dark:bg-blue-900/30' : 'bg-white dark:bg-gray-800'}
                    ${isExpanded ? 'bg-gray-50 dark:bg-gray-700' : ''}
                    ${dayTasks.length > 0 ? 'cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700' : ''}
                  `.trim()}
                >
                  <div
                    className={`
                      p-2 text-right text-sm text-gray-900 dark:text-gray-100
                      ${today ? 'font-bold' : ''}
                      ${weekend ? 'text-red-500 dark:text-red-400' : ''}
                    `.trim()}
                  >
                    {day}
                    {today && <span className="text-green-600 dark:text-green-400 ml-1">●</span>}
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
                          </span>
                        ))}
                      </div>
                    ) : (
                      <p className="text-gray-400 dark:text-gray-500 text-xs m-1">Нет задач</p>
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
                      <ul className="list-none p-0 m-0 max-h-48 overflow-y-auto">
                        {dayTasks.map((task, idx) => (
                          <li
                            key={task.id || idx}
                            className={`flex justify-between items-start p-2.5 bg-blue-50 dark:bg-blue-900/30 rounded mb-2 
                              border-l-4 
                              transition-colors duration-300 ease-in-out
                              ${task.status_id === completedStatusId ? 'border-green-500 dark:border-green-400' : 'border-blue-500 dark:border-blue-400'} 
                              break-words`}
                          >
                            <span className="flex-1 text-gray-900 dark:text-gray-100">{task.title}</span>

                            {task.status_id !== completedStatusId ? (
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  if (task.id) {
                                    markTaskAsCompleted(task.id, task.estimated_points || 10);
                                  }
                                }}
                                className="ml-2 text-green-600 dark:text-green-400 hover:text-green-800 dark:hover:text-green-300 transition-colors"
                                title="Отметить как выполненную"
                              >
                                ✓
                              </button>
                            ) : (
                              <span
                                className="ml-2 text-green-500 dark:text-green-400 opacity-70"
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
                              className="ml-2 text-red-500 dark:text-red-400 cursor-pointer text-xl leading-none flex-shrink-0 hover:text-red-700 dark:hover:text-red-300 transition-colors"
                              title="Удалить задачу"
                            >
                              ×
                            </button>
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
  );
};

export default HomePage;