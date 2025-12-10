// src/pages/HomePage.jsx
import React, { useState, useMemo, useRef, useEffect } from 'react';
import { useApi } from '../api/client.js'; // ✅ ваш существующий client.js

const getDaysInMonth = (year, month) => new Date(year, month + 1, 0).getDate();

const getFirstDayOfMonth = (year, month) => {
  const day = new Date(year, month, 1).getDay();
  return day === 0 ? 6 : day - 1; // 0 = Пн
};

const formatDateKey = (date) => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

// Лёгкое преобразование имени месяца в родительный падеж (только окончание)
const toGenitiveMonth = (name) => {
  if (name.endsWith('рь')) return name.slice(0, -1) + 'я'; // январь, сентябрь, октябрь, ноябрь, декабрь
  if (name.endsWith('ль')) return name.slice(0, -1) + 'я'; // апрель, февраль, июль
  if (name.endsWith('й')) return name.slice(0, -1) + 'я';  // май
  if (name.endsWith('нь')) return name.slice(0, -1) + 'я'; // июнь
  if (name.endsWith('т')) return name + 'а';               // март, август
  return name;
};

const HomePage = () => {
  const api = useApi(); // ✅ ваш клиент — уже работает с токеном

  useEffect(() => {
    document.title = 'Геймификация предприятий';
  }, []);

  // Состояние календаря (для UX-отображения отправленных сообщений)
  const [currentDate, setCurrentDate] = useState(new Date());
  const [expandedDay, setExpandedDay] = useState(null);
  const [tasks, setTasks] = useState(() => {
    const saved = localStorage.getItem('tasks');
    return saved ? JSON.parse(saved) : {};
  });

  // Состояние отправки
  const inputRef = useRef(null);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState(null);

  // ✅ Отправка на /chat в нужном формате
  const handleSendMessage = async (messageText) => {
    if (!messageText.trim()) return;

    setIsSending(true);
    setError(null);

    try {
      // Отправляем { "message": "текст" } на POST /chat
      const response = await api.post('/chat', { message: messageText });

      // ✅ Успех
      console.log('Ответ от /chat:', response);

      // Опционально: добавляем в локальный календарь на сегодня (для мгновенного отклика)
      const today = new Date();
      const dateKey = formatDateKey(today);
      const newTasks = {
        ...tasks,
        [dateKey]: [...(tasks[dateKey] || []), messageText]
      };
      localStorage.setItem('tasks', JSON.stringify(newTasks));
      setTasks(newTasks);
    } catch (err) {
      console.error('Ошибка отправки:', err);
      setError(err.message || 'Не удалось отправить сообщение');
      // Показываем ошибку в интерфейсе
    } finally {
      setIsSending(false);
      inputRef.current?.focus();
    }
  };

  // Остальная логика календаря (без изменений)
  const removeTask = (dateKey, taskIndex) => {
    const dayTasks = [...(tasks[dateKey] || [])];
    dayTasks.splice(taskIndex, 1);
    const newTasks = { ...tasks, [dateKey]: dayTasks };
    localStorage.setItem('tasks', JSON.stringify(newTasks));
    setTasks(newTasks);
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

  return (
    <div className="p-5 max-w-7xl mx-auto bg-gray-50 dark:bg-gray-900 min-h-screen">
      <header className="mb-8 px-2.5">
        <h1 className="m-0 text-gray-800 dark:text-gray-100 font-bold text-2xl">🎯 Gamification Dashboard</h1>
      </header>

      <div className="grid grid-cols-1 gap-8">
        {/* ✅ Панель чата — отправка на /chat */}
        <div className="bg-white dark:bg-gray-800 p-5 rounded-lg shadow-md">
          <h2 className="m-0 mb-5 text-gray-800 dark:text-gray-100 font-semibold text-xl">💬 Отправить сообщение</h2>
          <div className="flex gap-2.5">
            <input
              ref={inputRef}
              type="text"
              placeholder="Введите сообщение..."
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  const text = e.target.value.trim();
                  if (text) {
                    handleSendMessage(text);
                    e.target.value = '';
                  }
                }
              }}
              className="flex-1 px-2.5 py-2.5 border border-gray-300 dark:border-gray-600 rounded text-base bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <button
              onClick={() => {
                const text = inputRef.current?.value?.trim();
                if (text) {
                  handleSendMessage(text);
                  inputRef.current.value = '';
                }
              }}
              className="px-4 py-2.5 bg-green-500 text-white border-none rounded cursor-pointer font-medium hover:bg-green-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={isSending}
            >
              {isSending ? 'Отправка...' : '➤ Отправить'}
            </button>
          </div>
          {error && (
            <p className="text-red-500 dark:text-red-400 text-sm mt-2 p-1.5 bg-red-50 dark:bg-red-900/30 rounded">
              ❌ {error}
            </p>
          )}
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-2 leading-relaxed">
            Сообщение отправляется на <code className="bg-gray-100 dark:bg-gray-700 px-1 py-0.5 rounded text-xs">POST {import.meta.env.VITE_API_BASE_URL || ''}/chat</code>
            {' '}в формате: <code className="bg-gray-100 dark:bg-gray-700 px-1 py-0.5 rounded text-xs">{"{ \"message\": \"ваш текст\" }"}</code>
          </p>
        </div>

        {/* Календарь */}
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
                            key={i}
                            className="bg-cyan-50 dark:bg-cyan-900/50 text-cyan-900 dark:text-cyan-100 px-2 py-1 rounded-full text-xs inline-block max-w-full break-words m-0.5"
                          >
                            {task.length > 15 ? task.slice(0, 15) + '…' : task}
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
                            key={idx}
                            className="flex justify-between items-start p-2.5 bg-blue-50 dark:bg-blue-900/30 rounded mb-2 border-l-4 border-blue-500 dark:border-blue-400 break-words"
                          >
                            <span className="flex-1 text-gray-900 dark:text-gray-100">{task}</span>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                removeTask(dateKey, idx);
                              }}
                              className="bg-transparent border-none text-red-500 dark:text-red-400 cursor-pointer text-xl leading-none ml-2 flex-shrink-0 hover:text-red-700 dark:hover:text-red-300 transition-colors"
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