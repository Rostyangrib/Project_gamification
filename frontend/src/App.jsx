// src/App.jsx
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext.jsx';
import { ThemeProvider } from './context/ThemeContext.jsx';
import Navbar from './components/Navbar.jsx';
import HomePage from './pages/HomePage.jsx';
import AuthPage from './pages/AuthPage.jsx';
import LeaderboardsPage from './pages/LeaderboardsPage.jsx';
import ProfilePage from './pages/ProfilePage.jsx';
import ManagerPage from './pages/ManagerPage.jsx';
import AdminPage from './pages/AdminPage.jsx';

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <Router>
          <Navbar />
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/login" element={<AuthPage />} />
            <Route path="/leaderboards" element={<LeaderboardsPage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/manager" element={<ManagerPage />} />
            <Route path="/admin" element={<AdminPage />} />
          </Routes>
        </Router>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;