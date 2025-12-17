import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import { useApi } from '../api/client.js';

const ManagerPage = () => {
  const { isAuthenticated, user } = useAuth();
  const api = useApi();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

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
  const [competitions, setCompetitions] = useState([]);
  const [loadingCompetitions, setLoadingCompetitions] = useState(false);
  const [editingCompetition, setEditingCompetition] = useState(null);
  const [editFormData, setEditFormData] = useState({ title: '', start_date: '', end_date: '' });
  const [expandedCompetitionId, setExpandedCompetitionId] = useState(null);
  const [leaderboardData, setLeaderboardData] = useState({});
  const [loadingLeaderboard, setLoadingLeaderboard] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [managingParticipants, setManagingParticipants] = useState(null);
  const [competitionParticipants, setCompetitionParticipants] = useState({});
  const [loadingParticipants, setLoadingParticipants] = useState(false);
  const [participantSearchText, setParticipantSearchText] = useState('');
  const [editTasks, setEditTasks] = useState([{ title: '', user_ids: [] }]);

  useEffect(() => {
    document.title = 'Управление соревнованиями | Геймификация предприятий';
    const link = document.querySelector("link[rel~='icon']") || document.createElement('link');
    link.rel = 'icon';
    link.href = '/favicon-g.svg';
    document.head.appendChild(link);

    // Проверка авторизации и прав менеджера/администратора
    if (!isAuthenticated) {
      navigate('/login');
      return;
    }

    if (user?.role !== 'admin' && user?.role !== 'manager') {
      navigate('/');
      return;
    }

    loadUsers();
    loadCompetitions();
  }, [isAuthenticated, user, navigate]);

  // Обработка параметра competitionId из URL для автоматического раскрытия соревнования
  useEffect(() => {
    const competitionIdParam = searchParams.get('competitionId');
    if (competitionIdParam && competitions.length > 0) {
      const competitionId = parseInt(competitionIdParam);
      const competition = competitions.find(c => c.id === competitionId);
      if (competition) {
        const shouldLoadLeaderboard = !leaderboardData[competitionId] || expandedCompetitionId !== competitionId;
        
        const loadLeaderboardForCompetition = async () => {
          try {
            if (!leaderboardData[competitionId]) {
              setLoadingLeaderboard(true);
              const data = await api.get(`/leaderboard/${competitionId}`);
              setLeaderboardData(prev => ({ ...prev, [competitionId]: data || [] }));
            }
            if (expandedCompetitionId !== competitionId) {
              setExpandedCompetitionId(competitionId);
            }
            setTimeout(() => {
              const element = document.getElementById(`competition-${competitionId}`);
              if (element) {
                element.scrollIntoView({ behavior: 'smooth', block: 'start' });
              }
            }, 300);
            
            setTimeout(() => {
              setSearchParams({});
            }, 500);
          } catch (err) {
            console.error('Ошибка загрузки рейтинга:', err);
            if (expandedCompetitionId !== competitionId) {
              setExpandedCompetitionId(competitionId);
            }
            setTimeout(() => {
              setSearchParams({});
            }, 500);
          } finally {
            setLoadingLeaderboard(false);
          }
        };
        
        if (shouldLoadLeaderboard) {
          loadLeaderboardForCompetition();
        } else {
          if (expandedCompetitionId !== competitionId) {
            setExpandedCompetitionId(competitionId);
          }
          setTimeout(() => {
            const element = document.getElementById(`competition-${competitionId}`);
            if (element) {
              element.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
            // Удаляем параметр competitionId из URL
            setSearchParams({});
          }, 300);
        }
      } else {
        // Если соревнование не найдено, все равно удаляем параметр
        setSearchParams({});
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, competitions]);

  const loadUsers = async () => {
    try {
      setLoadingUsers(true);
      const users = await api.get('/users/only');
      setAllUsers(users || []);
    } catch (err) {
      console.error('Ошибка загрузки пользователей:', err);
      setError('Не удалось загрузить список пользователей');
    } finally {
      setLoadingUsers(false);
    }
  };

  const loadCompetitions = async () => {
    try {
      setLoadingCompetitions(true);
      const comps = await api.get('/competitions');
      setCompetitions(comps || []);
    } catch (err) {
      console.error('Ошибка загрузки соревнований:', err);
      setError('Не удалось загрузить список соревнований');
    } finally {
      setLoadingCompetitions(false);
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

  const selectAllUsers = () => {
    const allFilteredUserIds = filteredUsers.map(user => user.id);
    setSelectedUsers(allFilteredUserIds);
  };

  const deselectAllUsers = () => {
    setSelectedUsers([]);
    // Очищаем выбранных пользователей в задачах
    setTasks(currentTasks => 
      currentTasks.map(task => ({
        ...task,
        user_ids: []
      }))
    );
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

  // Функции для управления задачами в режиме редактирования
  const addEditTask = () => {
    setEditTasks(prev => [...prev, { title: '', user_ids: [] }]);
  };

  const removeEditTask = (index) => {
    setEditTasks(prev => prev.filter((_, i) => i !== index));
  };

  const updateEditTask = (index, field, value) => {
    setEditTasks(prev => {
      const updated = [...prev];
      updated[index] = { ...updated[index], [field]: value };
      return updated;
    });
  };

  const toggleEditTaskUser = (taskIndex, userId) => {
    setEditTasks(prev => {
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

  // Функция для форматирования даты для отправки на сервер
  // Отправляем дату в ISO формате с указанием, что это локальное время (без конвертации в UTC)
  const formatLocalDateTime = (dateInput) => {
    // dateInput может быть Date объектом или строкой из datetime-local input
    const date = typeof dateInput === 'string' ? new Date(dateInput) : dateInput;
    
    // Получаем компоненты локального времени
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');
    
    // Отправляем как ISO строка с явным указанием локального offset
    // Это позволит серверу правильно интерпретировать время
    const offset = -date.getTimezoneOffset();
    const offsetHours = String(Math.floor(Math.abs(offset) / 60)).padStart(2, '0');
    const offsetMinutes = String(Math.abs(offset) % 60).padStart(2, '0');
    const offsetSign = offset >= 0 ? '+' : '-';
    
    return `${year}-${month}-${day}T${hours}:${minutes}:${seconds}${offsetSign}${offsetHours}:${offsetMinutes}`;
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

    // Создаем даты в локальном времени (datetime-local уже в локальном часовом поясе)
    const startDate = new Date(formData.start_date);
    const endDate = new Date(formData.end_date);

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

      const competition = await api.post('/competitions', {
        title: formData.title.trim(),
        start_date: formatLocalDateTime(startDate),
        end_date: formatLocalDateTime(endDate)
      });

      const competitionId = typeof competition.id === 'string' ? parseInt(competition.id) : competition.id;

      const assignPromises = selectedUsers.map(userId =>
        api.put(`/users/${userId}/competition`, {
          competition_id: competitionId
        })
      );

      await Promise.all(assignPromises);

      for (let i = 0; i < validTasks.length; i++) {
        const task = validTasks[i];
        // Формируем сообщение для AI, которое создаст задачу
        const message = `Создай задачу "${task.title.trim()}"`;
        
        // Обновляем сообщение о прогрессе
        setSuccess(`Создание задач: ${i + 1} из ${validTasks.length}...`);
        
        // Отправляем запрос на создание задачи
        await api.post('/chat', { 
          message,
          user_ids: task.user_ids
        });

        if (i < validTasks.length - 1) {
          await new Promise(resolve => setTimeout(resolve, 300)); // 300ms задержка
        }
      }

      setSuccess('Соревнование и задачи успешно созданы!');
      
      // Очистка формы
      setFormData({ title: '', start_date: '', end_date: '' });
      setSelectedUsers([]);
      setTasks([{ title: '', user_ids: [] }]);

      // Обновляем список соревнований
      await loadCompetitions();

      // Автоматически скрыть сообщение успеха через 5 секунд
      setTimeout(() => setSuccess(''), 5000);
    } catch (err) {
      console.error('Ошибка создания соревнования:', err);
      setError(err.message || 'Не удалось создать соревнование');
    } finally {
      setLoading(false);
    }
  };

  const handleEditCompetition = async (competition) => {
    setEditingCompetition(competition);
    const startDate = new Date(competition.start_date);
    const endDate = new Date(competition.end_date);
    // Форматируем даты для input datetime-local (YYYY-MM-DDTHH:mm)
    const formatDateTimeLocal = (date) => {
      const d = new Date(date);
      const year = d.getFullYear();
      const month = String(d.getMonth() + 1).padStart(2, '0');
      const day = String(d.getDate()).padStart(2, '0');
      const hours = String(d.getHours()).padStart(2, '0');
      const minutes = String(d.getMinutes()).padStart(2, '0');
      return `${year}-${month}-${day}T${hours}:${minutes}`;
    };
    setEditFormData({
      title: competition.title,
      start_date: formatDateTimeLocal(startDate),
      end_date: formatDateTimeLocal(endDate)
    });
    // Инициализируем задачи для редактирования
    setEditTasks([{ title: '', user_ids: [] }]);
    // Загружаем участников соревнования
    await loadCompetitionParticipants(competition.id);
  };

  const handleCancelEdit = () => {
    setEditingCompetition(null);
    setEditFormData({ title: '', start_date: '', end_date: '' });
    setEditTasks([{ title: '', user_ids: [] }]);
    setError('');
  };

  // Загрузка участников соревнования
  const loadCompetitionParticipants = async (competitionId) => {
    try {
      setLoadingParticipants(true);
      // Получаем всех пользователей
      const users = await api.get('/users/only');
      // Фильтруем тех, кто участвует в данном соревновании
      const participants = users.filter(user => user.cur_comp === competitionId).map(user => user.id);
      setCompetitionParticipants(prev => ({
        ...prev,
        [competitionId]: participants
      }));
    } catch (err) {
      console.error('Ошибка загрузки участников:', err);
      setError('Не удалось загрузить участников соревнования');
    } finally {
      setLoadingParticipants(false);
    }
  };

  // Открытие/закрытие управления участниками (toggle)
  const handleManageParticipants = async (competitionId) => {
    // Если уже открыто для этого соревнования - закрываем
    if (managingParticipants === competitionId) {
      setManagingParticipants(null);
      setParticipantSearchText('');
      return;
    }
    setManagingParticipants(competitionId);
    setParticipantSearchText('');
    await loadCompetitionParticipants(competitionId);
  };

  // Добавление участника в соревнование
  const handleAddParticipant = async (competitionId, userId) => {
    try {
      setLoading(true);
      await api.put(`/users/${userId}/competition`, {
        competition_id: competitionId
      });
      
      await loadCompetitionParticipants(competitionId);
      setSuccess('Участник успешно добавлен в соревнование!');
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      console.error('Ошибка добавления участника:', err);
      setError(err.message || 'Не удалось добавить участника');
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveParticipant = async (competitionId, userId) => {
    try {
      setLoading(true);
      await api.put(`/users/${userId}/competition`, {
        competition_id: null
      });
      
      await loadCompetitionParticipants(competitionId);
      setSuccess('Участник успешно удалён из соревнования!');
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      console.error('Ошибка удаления участника:', err);
      setError(err.message || 'Не удалось удалить участника');
    } finally {
      setLoading(false);
    }
  };

  const getFilteredUsersForParticipants = () => {
    if (!allUsers.length) return [];
    
    return allUsers.filter(user => {
      const matchesSearch = participantSearchText.trim() === '' || 
        `${user.first_name} ${user.last_name} ${user.email}`.toLowerCase().includes(participantSearchText.toLowerCase());
      return matchesSearch;
    });
  };

  const handleUpdateCompetition = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!editFormData.title.trim()) {
      setError('Введите название соревнования');
      return;
    }

    if (!editFormData.start_date || !editFormData.end_date) {
      setError('Заполните все поля дат');
      return;
    }

    const startDate = new Date(editFormData.start_date);
    const endDate = new Date(editFormData.end_date);

    if (endDate <= startDate) {
      setError('Дедлайн должен быть позже даты начала');
      return;
    }

    // Валидация задач (если они добавлены)
    const validEditTasks = editTasks.filter(t => t.title.trim() && t.user_ids.length > 0);
    if (editTasks.some(t => t.title.trim() || t.user_ids.length > 0) && validEditTasks.length === 0) {
      setError('Заполните все добавленные задачи: укажите название и выберите пользователей');
      return;
    }

    try {
      setLoading(true);
      await api.put(`/competitions/${editingCompetition.id}`, {
        title: editFormData.title.trim(),
        start_date: formatLocalDateTime(startDate),
        end_date: formatLocalDateTime(endDate)
      });
      
      // Отправляем задачи через /chat, если они были добавлены
      // Используем дедлайн из формы редактирования (endDate), который был указан пользователем
      if (validEditTasks.length > 0) {
        for (let i = 0; i < validEditTasks.length; i++) {
          const task = validEditTasks[i];
          const message = `Создай задачу "${task.title.trim()}"`;
          
          setSuccess(`Обновление соревнования и создание задач: ${i + 1} из ${validEditTasks.length}...`);
          
          await api.post('/chat', { 
            message,
            user_ids: task.user_ids
          });

          if (i < validEditTasks.length - 1) {
            await new Promise(resolve => setTimeout(resolve, 300));
          }
        }
        setSuccess('Соревнование успешно обновлено и задачи добавлены!');
      } else {
        setSuccess('Соревнование успешно обновлено!');
      }
      
      setEditingCompetition(null);
      setEditFormData({ title: '', start_date: '', end_date: '' });
      setEditTasks([{ title: '', user_ids: [] }]);
      await loadCompetitions();
      
      setTimeout(() => setSuccess(''), 5000);
    } catch (err) {
      console.error('Ошибка обновления соревнования:', err);
      setError(err.message || 'Не удалось обновить соревнование');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteCompetition = async (competitionId) => {
    if (!window.confirm('Вы уверены, что хотите удалить это соревнование? Все пользователи будут отписаны от него.')) {
      return;
    }

    try {
      setLoading(true);
      await api.delete(`/competitions/${competitionId}`);
      setSuccess('Соревнование успешно удалено!');
      await loadCompetitions();
      setTimeout(() => setSuccess(''), 5000);
    } catch (err) {
      console.error('Ошибка удаления соревнования:', err);
      setError(err.message || 'Не удалось удалить соревнование');
    } finally {
      setLoading(false);
    }
  };

  // Функция для форматирования даты при отображении
  // Обрабатывает даты, которые приходят с сервера как naive datetime (без timezone)
  // Интерпретируем их как локальное время пользователя
  const formatDateTime = (dateString) => {
    if (!dateString) return '';
    
    // Если строка не имеет timezone info (формат "YYYY-MM-DDTHH:mm:ss" или "YYYY-MM-DDTHH:mm:ss.ffff"),
    // то интерпретируем её как локальное время
    let date;
    if (dateString.includes('Z') || dateString.match(/[+-]\d{2}:\d{2}$/)) {
      // Есть timezone info, используем как есть
      date = new Date(dateString);
    } else {
      // Нет timezone info - интерпретируем как локальное время
      // Добавляем явно, что это локальное время, создавая Date через компоненты
      const dateMatch = dateString.match(/(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})/);
      if (dateMatch) {
        const [, year, month, day, hours, minutes, seconds] = dateMatch;
        date = new Date(parseInt(year), parseInt(month) - 1, parseInt(day), 
                       parseInt(hours), parseInt(minutes), parseInt(seconds || 0));
      } else {
        date = new Date(dateString);
      }
    }
    
    if (isNaN(date.getTime())) return dateString;
    
    return date.toLocaleString('ru-RU', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getCompetitionStatus = (competition) => {
    const now = new Date();
    const startDate = new Date(competition.start_date);
    const endDate = new Date(competition.end_date);
    
    if (now < startDate) {
      return { text: 'Не началось', color: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300' };
    } else if (now >= startDate && now <= endDate) {
      return { text: 'Идёт', color: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300' };
    } else {
      return { text: 'Завершено', color: 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300' };
    }
  };

  const toggleLeaderboard = async (competitionId) => {
    if (expandedCompetitionId === competitionId) {
      setExpandedCompetitionId(null);
      return;
    }

    if (leaderboardData[competitionId]) {
      setExpandedCompetitionId(competitionId);
      return;
    }

    try {
      setLoadingLeaderboard(true);
      const data = await api.get(`/leaderboard/${competitionId}`);
      setLeaderboardData(prev => ({ ...prev, [competitionId]: data || [] }));
      setExpandedCompetitionId(competitionId);
    } catch (err) {
      console.error('Ошибка загрузки рейтинга:', err);
      setError('Не удалось загрузить рейтинг соревнования');
    } finally {
      setLoadingLeaderboard(false);
    }
  };

  const filteredUsers = allUsers.filter((user) => {
    if (!searchText.trim()) {
      return true;
    }

    const query = searchText.trim().toLowerCase();
    const fullName = `${user.first_name} ${user.last_name}`.toLowerCase();
    const email = (user.email || '').toLowerCase();
    
    return fullName.includes(query) || email.includes(query);
  });

  if (!isAuthenticated || (user?.role !== 'admin' && user?.role !== 'manager')) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-4 sm:p-6">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl sm:text-4xl font-bold text-gray-800 dark:text-gray-100 mb-2">
            Управление соревнованиями
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Просматривайте, редактируйте и создавайте новые соревнования
          </p>
        </div>

        {/* Список существующих соревнований */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 sm:p-8 mb-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold text-gray-800 dark:text-gray-100">
              Существующие соревнования
            </h2>
            <button
              onClick={loadCompetitions}
              disabled={loadingCompetitions}
              className="px-4 py-2 text-sm bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 rounded-lg hover:bg-indigo-200 dark:hover:bg-indigo-900/50 transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              <svg className={`w-4 h-4 ${loadingCompetitions ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Обновить
            </button>
          </div>

          {loadingCompetitions ? (
            <div className="text-center py-8">
              <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-indigo-500 border-t-transparent"></div>
              <p className="mt-2 text-gray-600 dark:text-gray-400">Загрузка соревнований...</p>
            </div>
          ) : competitions.length === 0 ? (
            <p className="text-gray-500 dark:text-gray-400 text-center py-8">
              Нет созданных соревнований
            </p>
          ) : (
            <div className="space-y-4">
              {competitions.map((competition) => (
                <div
                  key={competition.id}
                  id={`competition-${competition.id}`}
                  className="border border-gray-300 dark:border-gray-600 rounded-lg p-4 hover:shadow-md transition-shadow"
                >
                  {editingCompetition?.id === competition.id ? (
                    // Форма редактирования
                    <form onSubmit={handleUpdateCompetition} className="space-y-4">
                      <div>
                        <label className="block mb-1 text-sm font-medium text-gray-700 dark:text-gray-300">
                          Название *
                        </label>
                        <input
                          type="text"
                          value={editFormData.title}
                          onChange={(e) => setEditFormData({ ...editFormData, title: e.target.value })}
                          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                          required
                        />
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div>
                          <label className="block mb-1 text-sm font-medium text-gray-700 dark:text-gray-300">
                            Дата начала *
                          </label>
                          <input
                            type="datetime-local"
                            value={editFormData.start_date}
                            onChange={(e) => setEditFormData({ ...editFormData, start_date: e.target.value })}
                            min="1900-01-01T00:00"
                            max="9999-12-31T23:59"
                            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                            required
                          />
                        </div>
                        <div>
                          <label className="block mb-1 text-sm font-medium text-gray-700 dark:text-gray-300">
                            Дедлайн *
                          </label>
                          <input
                            type="datetime-local"
                            value={editFormData.end_date}
                            onChange={(e) => setEditFormData({ ...editFormData, end_date: e.target.value })}
                            min={editFormData.start_date || "1900-01-01T00:00"}
                            max="9999-12-31T23:59"
                            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                            required
                          />
                        </div>
                      </div>
                      
                      {/* Добавление задач */}
                      <div>
                        <div className="flex justify-between items-center mb-3">
                          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                            Добавить задачи ({editTasks.filter(t => t.title.trim() && t.user_ids.length > 0).length} добавлено)
                          </label>
                          <button
                            type="button"
                            onClick={addEditTask}
                            className="px-3 py-1.5 text-sm bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 rounded-lg hover:bg-indigo-200 dark:hover:bg-indigo-900/50 transition-colors flex items-center gap-1"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                            </svg>
                            Добавить задачу
                          </button>
                        </div>
                        
                        <div className="space-y-4">
                          {editTasks.map((task, index) => (
                            <div key={index} className="border border-gray-300 dark:border-gray-600 rounded-lg p-4 bg-gray-50 dark:bg-gray-700/30">
                              <div className="flex justify-between items-start mb-3">
                                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                                  Задача #{index + 1}
                                </span>
                                {editTasks.length > 1 && (
                                  <button
                                    type="button"
                                    onClick={() => removeEditTask(index)}
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
                                    onChange={(e) => updateEditTask(index, 'title', e.target.value)}
                                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                                    placeholder="Введите название задачи"
                                  />
                                </div>
                                
                                <div>
                                  <label className="block mb-1 text-xs font-medium text-gray-600 dark:text-gray-400">
                                    Пользователи * ({task.user_ids.length} выбрано)
                                  </label>
                                  <div className="border border-gray-300 dark:border-gray-600 rounded-lg p-2 max-h-40 overflow-y-auto bg-white dark:bg-gray-700">
                                    {loadingParticipants ? (
                                      <p className="text-xs text-gray-500 dark:text-gray-400 text-center py-2">
                                        Загрузка участников...
                                      </p>
                                    ) : !competitionParticipants[editingCompetition.id] || competitionParticipants[editingCompetition.id]?.length === 0 ? (
                                      <p className="text-xs text-gray-500 dark:text-gray-400 text-center py-2">
                                        Нет участников в этом соревновании
                                      </p>
                                    ) : (
                                      <div className="space-y-1">
                                        {allUsers
                                          .filter(userItem => competitionParticipants[editingCompetition.id]?.includes(userItem.id))
                                          .map((userItem) => (
                                            <label
                                              key={userItem.id}
                                              className="flex items-center p-2 rounded cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors"
                                            >
                                              <input
                                                type="checkbox"
                                                checked={task.user_ids.includes(userItem.id)}
                                                onChange={() => toggleEditTaskUser(index, userItem.id)}
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
                          ))}
                        </div>
                      </div>
                      
                      <div className="flex gap-2">
                        <button
                          type="submit"
                          disabled={loading}
                          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
                        >
                          Сохранить
                        </button>
                        <button
                          type="button"
                          onClick={handleCancelEdit}
                          disabled={loading}
                          className="px-4 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
                        >
                          Отмена
                        </button>
                      </div>
                    </form>
                  ) : (
                    <div>
                      <div className="flex justify-between items-start mb-3">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            <h3 className="text-xl font-bold text-gray-800 dark:text-gray-100">
                              {competition.title}
                            </h3>
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${getCompetitionStatus(competition).color}`}>
                              {getCompetitionStatus(competition).text}
                            </span>
                          </div>
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm text-gray-600 dark:text-gray-400">
                            <div>
                              <span className="font-semibold">Начало:</span> {formatDateTime(competition.start_date)}
                            </div>
                            <div>
                              <span className="font-semibold">Дедлайн:</span> {formatDateTime(competition.end_date)}
                            </div>
                            <div>
                              <span className="font-semibold">Создано:</span> {formatDateTime(competition.created_at)}
                            </div>
                          </div>
                        </div>
                        <div className="flex gap-2 ml-4">
                          <button
                            onClick={() => handleManageParticipants(competition.id)}
                            disabled={loading}
                            className="px-3 py-2 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded-lg hover:bg-green-200 dark:hover:bg-green-900/50 transition-colors disabled:opacity-50"
                            title="Управление участниками"
                          >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                            </svg>
                          </button>
                          <button
                            onClick={() => toggleLeaderboard(competition.id)}
                            disabled={loading || loadingLeaderboard}
                            className="px-3 py-2 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded-lg hover:bg-purple-200 dark:hover:bg-purple-900/50 transition-colors disabled:opacity-50"
                            title="Показать рейтинг"
                          >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />
                            </svg>
                          </button>
                          <button
                            onClick={() => handleEditCompetition(competition)}
                            disabled={loading}
                            className="px-3 py-2 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-lg hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-colors disabled:opacity-50"
                            title="Редактировать"
                          >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                            </svg>
                          </button>
                          <button
                            onClick={() => handleDeleteCompetition(competition.id)}
                            disabled={loading}
                            className="px-3 py-2 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded-lg hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors disabled:opacity-50"
                            title="Удалить"
                          >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        </div>
                      </div>
                      
                      {/* Рейтинг соревнования */}
                      {expandedCompetitionId === competition.id && (
                        <div className="mt-4 pt-4 border-t border-gray-300 dark:border-gray-600">
                          <h4 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-3">
                            🏆 Рейтинг участников
                          </h4>
                          {loadingLeaderboard ? (
                            <div className="text-center py-4">
                              <div className="inline-block h-6 w-6 animate-spin rounded-full border-4 border-indigo-500 border-t-transparent"></div>
                              <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">Загрузка рейтинга...</p>
                            </div>
                          ) : leaderboardData[competition.id]?.length > 0 ? (
                            <div className="space-y-2">
                              {leaderboardData[competition.id].map((user, index) => (
                                <div
                                  key={index}
                                  className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/30 rounded-lg"
                                >
                                  <div className="flex items-center gap-3">
                                    <span className="text-lg font-bold text-indigo-600 dark:text-indigo-400 w-8">
                                      {index + 1}
                                    </span>
                                    <span className="text-sm font-medium text-gray-800 dark:text-gray-100">
                                      {user.first_name} {user.last_name}
                                    </span>
                                  </div>
                                  <span className="text-sm font-bold text-indigo-600 dark:text-indigo-400">
                                    {user.total_points} баллов
                                  </span>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
                              Нет участников в этом соревновании
                            </p>
                          )}
                        </div>
                      )}
                      
                      {/* Управление участниками */}
                      {managingParticipants === competition.id && (
                        <div className="mt-4 pt-4 border-t border-gray-300 dark:border-gray-600">
                          <h4 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">
                            👥 Управление участниками
                          </h4>
                          
                          {/* Поиск пользователей */}
                          <div className="mb-4">
                            <input
                              type="text"
                              placeholder="Найти участника"
                              value={participantSearchText}
                              onChange={(e) => setParticipantSearchText(e.target.value)}
                              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                            />
                          </div>

                          {loadingParticipants ? (
                            <div className="text-center py-4">
                              <div className="inline-block h-6 w-6 animate-spin rounded-full border-4 border-indigo-500 border-t-transparent"></div>
                              <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">Загрузка участников...</p>
                            </div>
                          ) : (
                            <div className="space-y-2 max-h-64 overflow-y-auto">
                              {getFilteredUsersForParticipants().map((user) => {
                                const isParticipant = competitionParticipants[competition.id]?.includes(user.id) || false;
                                return (
                                  <div
                                    key={user.id}
                                    className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/30 rounded-lg"
                                  >
                                    <div className="flex items-center gap-3">
                                      <div>
                                        <span className="text-sm font-medium text-gray-800 dark:text-gray-100">
                                          {user.first_name} {user.last_name}
                                        </span>
                                        <span className="text-xs text-gray-500 dark:text-gray-400 block">
                                          {user.email}
                                        </span>
                                      </div>
                                      {isParticipant && (
                                        <span className="px-2 py-1 text-xs font-medium bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded">
                                          Участник
                                        </span>
                                      )}
                                    </div>
                                    {isParticipant ? (
                                      <button
                                        onClick={() => handleRemoveParticipant(competition.id, user.id)}
                                        disabled={loading}
                                        className="px-3 py-1 text-sm bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded-lg hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors disabled:opacity-50"
                                      >
                                        Удалить
                                      </button>
                                    ) : (
                                      <button
                                        onClick={() => handleAddParticipant(competition.id, user.id)}
                                        disabled={loading}
                                        className="px-3 py-1 text-sm bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 rounded-lg hover:bg-indigo-200 dark:hover:bg-indigo-900/50 transition-colors disabled:opacity-50"
                                      >
                                        Добавить
                                      </button>
                                    )}
                                  </div>
                                );
                              })}
                              {getFilteredUsersForParticipants().length === 0 && (
                                <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
                                  Пользователи не найдены
                                </p>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Форма создания нового соревнования */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 sm:p-8">
          <h2 className="text-2xl font-bold text-gray-800 dark:text-gray-100 mb-6">
            Создать новое соревнование
          </h2>
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
                min="1900-01-01T00:00"
                max="9999-12-31T23:59"
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
                min={formData.start_date || "1900-01-01T00:00"}
                max="9999-12-31T23:59"
                className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                required
              />
            </div>

            {/* Выбор участников */}
            <div>
              <div className="flex justify-between items-center mb-3">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Участники соревнования * ({selectedUsers.length} выбрано)
                </label>
                {!loadingUsers && filteredUsers.length > 0 && (
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={selectAllUsers}
                      className="px-3 py-1.5 text-xs bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 rounded-lg hover:bg-indigo-200 dark:hover:bg-indigo-900/50 transition-colors"
                    >
                      Выбрать всех
                    </button>
                    {selectedUsers.length > 0 && (
                      <button
                        type="button"
                        onClick={deselectAllUsers}
                        className="px-3 py-1.5 text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                      >
                        Снять выбор
                      </button>
                    )}
                  </div>
                )}
              </div>
              
              {/* Поиск */}
              {!loadingUsers && allUsers.length > 0 && (
                <div className="mb-3">
                  <input
                    type="text"
                    value={searchText}
                    onChange={(e) => setSearchText(e.target.value)}
                    placeholder="Найти участника"
                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  />
                  {searchText && (
                    <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                      Найдено: {filteredUsers.length} из {allUsers.length}
                    </p>
                  )}
                </div>
              )}
              
              {loadingUsers ? (
                <div className="text-center py-8">
                  <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-indigo-500 border-t-transparent"></div>
                  <p className="mt-2 text-gray-600 dark:text-gray-400">Загрузка пользователей...</p>
                </div>
              ) : allUsers.length === 0 ? (
                <p className="text-gray-500 dark:text-gray-400 text-center py-4">
                  Нет доступных пользователей
                </p>
              ) : filteredUsers.length === 0 ? (
                <div className="border border-gray-300 dark:border-gray-600 rounded-lg p-4 bg-gray-50 dark:bg-gray-700/30">
                  <p className="text-gray-500 dark:text-gray-400 text-center py-4">
                    Пользователи не найдены по заданным критериям
                  </p>
                </div>
              ) : (
                <div className="border border-gray-300 dark:border-gray-600 rounded-lg p-4 max-h-96 overflow-y-auto bg-gray-50 dark:bg-gray-700/30">
                  <div className="space-y-2">
                    {filteredUsers.map((userItem) => (
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

