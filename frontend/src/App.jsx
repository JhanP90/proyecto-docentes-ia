// src/App.jsx
import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ToastProvider } from './contexts/ToastContext';

import AppLayout from './components/Layout/AppLayout';

// Auth pages
import LoginPage from './pages/auth/LoginPage';
import RegisterPage from './pages/auth/RegisterPage';

// Aspirante pages
import DashboardPage from './pages/aspirante/DashboardPage';
import UploadPage from './pages/aspirante/UploadPage';
import ValidarPage from './pages/aspirante/ValidarPage';
import ResultadoPage from './pages/aspirante/ResultadoPage';

// Admin pages
import AdminDashboard from './pages/admin/AdminDashboard';
import ReglasPage from './pages/admin/ReglasPage';

import { Loader2 } from 'lucide-react';

function ProtectedRoute({ requireAdmin = false }) {
  const { user, loading, isAdmin } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <Loader2 size={32} className="animate-spin text-blue-600" />
      </div>
    );
  }

  if (!user) return <Navigate to="/login" replace />;
  if (requireAdmin && !isAdmin) return <Navigate to="/dashboard" replace />;
  if (!requireAdmin && isAdmin) return <Navigate to="/admin/dashboard" replace />;

  return <Outlet />;
}

export default function App() {
  return (
    <BrowserRouter>
      <ToastProvider>
        <AuthProvider>
          <Routes>
            <Route path="/" element={<Navigate to="/login" replace />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />

            {/* Aspirante routes */}
            <Route element={<ProtectedRoute requireAdmin={false} />}>
              <Route element={<AppLayout />}>
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/upload" element={<UploadPage />} />
                <Route path="/validar" element={<ValidarPage />} />
                <Route path="/resultado" element={<ResultadoPage />} />
              </Route>
            </Route>

            {/* Admin routes */}
            <Route element={<ProtectedRoute requireAdmin={true} />}>
              <Route element={<AppLayout />}>
                <Route path="/admin/dashboard" element={<AdminDashboard />} />
                <Route path="/admin/reglas" element={<ReglasPage />} />
              </Route>
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AuthProvider>
      </ToastProvider>
    </BrowserRouter>
  );
}
