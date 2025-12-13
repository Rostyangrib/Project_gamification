import React, { createContext, useContext, useState, useEffect } from 'react';

const ThemeContext = createContext();

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
};

export const ThemeProvider = ({ children }) => {
  // Определяем системную тему
  const getSystemTheme = () => {
    if (typeof window !== 'undefined' && window.matchMedia) {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    return 'light';
  };

  // Загружаем сохранённую тему или используем системную
  const [theme, setTheme] = useState(() => {
    const saved = localStorage.getItem('theme');
    if (saved === 'light' || saved === 'dark') {
      return saved;
    }
    return getSystemTheme();
  });

  // Применяем тему к документу
  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
    localStorage.setItem('theme', theme);
  }, [theme]);

  // Слушаем изменения системной темы при первой загрузке
  useEffect(() => {
    if (typeof window !== 'undefined' && window.matchMedia) {
      const saved = localStorage.getItem('theme');
      // Если тема не была сохранена, используем системную
      if (!saved) {
        const systemTheme = getSystemTheme();
        setTheme(systemTheme);
      }
    }
  }, []);

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

