// src/pages/HomePage.jsx
import React, { useState, useMemo, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import { useApi } from '../api/client.js'; // ✅ ваш существующий client.js
import styles from '../styles/HomePage.module.css';

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

const HomePage = () => {
  const { isLoggedIn, logout } = useAuth();
  const api = useApi(); // ✅ ваш клиент — уже работает с токеном
  const navigate = useNavigate();

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
      alert('✅ Сообщение отправлено!');
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
    <div className={styles.container}>
      <header className={styles.header}>
        <h1 className={styles.title}>🎯 Gamification Dashboard</h1>
        <button
          onClick={() => isLoggedIn ? (logout(), navigate('/login')) : navigate('/login')}
          className={isLoggedIn ? styles.authBtn_logout : styles.authBtn_login}
        >
          {isLoggedIn ? 'Выйти' : 'Войти'}
        </button>
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '30px' }}>
        {/* ✅ Панель чата — отправка на /chat */}
        <div className={styles.quickAdd}>
          <h2 className={styles.quickAddTitle}>💬 Отправить сообщение</h2>
          <div className={styles.inputGroup}>
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
              className={styles.taskInput}
            />
            <button
              onClick={() => {
                const text = inputRef.current?.value?.trim();
                if (text) {
                  handleSendMessage(text);
                  inputRef.current.value = '';
                }
              }}
              className={styles.addBtn}
              disabled={isSending}
            >
              {isSending ? 'Отправка...' : '➤ Отправить'}
            </button>
          </div>
          {error && (
            <p className={styles.error} style={{
              color: '#e74c3c',
              fontSize: '0.85rem',
              marginTop: '8px',
              padding: '6px',
              backgroundColor: '#fdf2f2',
              borderRadius: '4px'
            }}>
              ❌ {error}
            </p>
          )}
          <p className={styles.hint}>
            Сообщение отправляется на <code>POST {import.meta.env.VITE_API_BASE_URL || ''}/chat</code>
            в формате: <code>{"{ \"message\": \"ваш текст\" }"}</code>
          </p>
        </div>

        {/* Календарь — без изменений */}
        <div className={styles.calendar}>
          <div className={styles.calendarHeader}>
            <h2 className={styles.monthTitle}>
              📅 {new Date(year, month).toLocaleString('ru-RU', { month: 'long', year: 'numeric' })}
            </h2>
            <div className={styles.navBtns}>
              <button onClick={goToToday} className={styles.navBtn_today}>
                Сегодня
              </button>
              <button onClick={goToPreviousMonth} className={styles.navBtn_month}>
                ‹
              </button>
              <button onClick={goToNextMonth} className={styles.navBtn_month}>
                ›
              </button>
            </div>
          </div>

          <div className={styles.weekdays}>
            {['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'].map(day => (
              <div
                key={day}
                className={day === 'Сб' || day === 'Вс' ? styles.weekday_weekend : ''}
              >
                {day}
              </div>
            ))}
          </div>

          <div className={styles.daysGrid}>
            {Array.from({ length: startDay }).map((_, i) => (
              <div key={`empty-${i}`} style={{ height: '120px' }}></div>
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
                    ${styles.dayCell}
                    ${today ? styles.dayCell_today : ''}
                    ${isExpanded ? styles.dayCell_expanded : ''}
                    ${dayTasks.length > 0 ? styles.dayCell_interactive : ''}
                  `.trim()}
                >
                  <div
                    className={`
                      ${styles.dayHeader}
                      ${today ? styles.dayHeader_today : ''}
                      ${weekend ? styles.dayHeader_weekend : ''}
                    `.trim()}
                  >
                    {day}
                    {today && <span className={styles.todayDot}>●</span>}
                  </div>

                  <div className={styles.tasksPreview}>
                    {dayTasks.length > 0 ? (
                      <div>
                        {dayTasks.map((task, i) => (
                          <span key={i} className={styles.taskTag}>
                            {task.length > 15 ? task.slice(0, 15) + '…' : task}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <p className={styles.noTasks}>Нет задач</p>
                    )}
                  </div>

                  {dayTasks.length > 0 && !isExpanded && (
                    <div className={styles.expandHint}>Кликните для просмотра</div>
                  )}

                  {isExpanded && dayTasks.length > 0 && (
                    <div className={styles.expandedPanel}>
                      <div className={styles.expandedTitle}>
                        Задачи на {day} {new Date(year, month).toLocaleString('ru-RU', { month: 'long' })}:
                      </div>
                      <ul className={styles.tasksList}>
                        {dayTasks.map((task, idx) => (
                          <li key={idx} className={styles.taskItem}>
                            <span>{task}</span>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                removeTask(dateKey, idx);
                              }}
                              className={styles.deleteBtn}
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