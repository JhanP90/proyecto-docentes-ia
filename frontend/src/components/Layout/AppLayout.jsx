// src/components/Layout/AppLayout.jsx
import React, { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import {
  LayoutDashboard, Upload, CheckSquare, Trophy, Settings, Users,
  GraduationCap, LogOut, Menu, X, ChevronRight
} from 'lucide-react';

const ASPIRANTE_NAV = [
  { path: '/dashboard', icon: LayoutDashboard, label: 'Mi Panel' },
  { path: '/upload', icon: Upload, label: 'Subir CV' },
  { path: '/validar', icon: CheckSquare, label: 'Validar Datos' },
  { path: '/resultado', icon: Trophy, label: 'Mi Resultado' },
];

const ADMIN_NAV = [
  { path: '/admin/dashboard', icon: Users, label: 'Postulantes' },
  { path: '/admin/reglas', icon: Settings, label: 'Motor de Reglas' },
];

export default function AppLayout() {
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const navItems = isAdmin ? ADMIN_NAV : ASPIRANTE_NAV;

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">
      {/* Sidebar overlay mobile */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-30 bg-black/30 backdrop-blur-sm lg:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed lg:static inset-y-0 left-0 z-40 w-64 bg-white border-r border-slate-200/80 flex flex-col transform transition-transform duration-300 lg:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Brand */}
        <div className="p-5 border-b border-slate-100">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-xl flex items-center justify-center shadow-md">
              <GraduationCap size={20} className="text-white" />
            </div>
            <div>
              <p className="font-bold text-slate-800 text-sm leading-tight">Univ. de Caldas</p>
              <p className="text-xs text-slate-400">Reclutamiento Docente</p>
            </div>
          </div>
        </div>

        {/* User card */}
        <div className="px-4 py-3">
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl p-3 border border-blue-100/50">
            <p className="text-sm font-semibold text-slate-800 truncate">{user?.nombres} {user?.apellidos}</p>
            <p className="text-xs text-blue-600 mt-0.5 capitalize font-medium">
              {isAdmin ? 'Administrador' : 'Aspirante Docente'}
            </p>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-2 space-y-1 overflow-y-auto">
          {navItems.map(({ path, icon: Icon, label }) => {
            const active = location.pathname === path;
            return (
              <button
                key={path}
                onClick={() => { navigate(path); setSidebarOpen(false); }}
                className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 text-left group ${
                  active
                    ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-md shadow-blue-500/20'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-800'
                }`}
              >
                <Icon size={18} className={active ? 'text-white/90' : 'text-slate-400 group-hover:text-slate-600'} />
                {label}
                {active && <ChevronRight size={14} className="ml-auto text-white/70" />}
              </button>
            );
          })}
        </nav>

        {/* Logout */}
        <div className="p-3 border-t border-slate-100">
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium text-red-600 hover:bg-red-50 transition-colors"
          >
            <LogOut size={18} />
            Cerrar Sesión
          </button>
        </div>
      </aside>

      {/* Main content area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <header className="bg-white/80 backdrop-blur-sm border-b border-slate-200/80 px-4 lg:px-8 py-3 flex items-center gap-4 sticky top-0 z-20">
          <button className="lg:hidden p-2 rounded-lg hover:bg-slate-100 transition" onClick={() => setSidebarOpen(true)}>
            <Menu size={20} className="text-slate-600" />
          </button>
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <span className="font-semibold text-slate-800">{isAdmin ? 'Panel Administrativo' : 'Portal del Aspirante'}</span>
            <ChevronRight size={14} />
            <span className="text-blue-600 font-medium">
              {navItems.find((i) => i.path === location.pathname)?.label || 'Inicio'}
            </span>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-4 lg:p-8">
          <div className="max-w-6xl mx-auto fade-in">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
