// src/pages/aspirante/DashboardPage.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useToast } from '../../contexts/ToastContext';
import { hojasAPI, evaluacionAPI } from '../../api/client';
import {
  FileText, Bot, BarChart3, Award, Upload, CheckSquare, Trophy,
  RefreshCw, Loader2, AlertCircle, ChevronRight, Sparkles
} from 'lucide-react';

const STEPS = [
  { key: 'upload', icon: Upload, label: 'Subir CV', desc: 'Carga tu hoja de vida en PDF' },
  { key: 'ia', icon: Bot, label: 'Análisis IA', desc: 'Gemini extrae tus datos' },
  { key: 'validar', icon: CheckSquare, label: 'Validar', desc: 'Revisa y confirma datos' },
  { key: 'resultado', icon: Trophy, label: 'Resultado', desc: 'Consulta tu puntaje' },
];

function StatCard({ icon: Icon, label, value, sub, color, onClick }) {
  return (
    <div
      onClick={onClick}
      className={`bg-white rounded-2xl border border-slate-100 p-5 shadow-sm hover:shadow-md transition-all duration-300 ${
        onClick ? 'cursor-pointer hover:-translate-y-1' : ''
      }`}
    >
      <div className="flex items-start justify-between mb-3">
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center`} style={{ backgroundColor: `${color}15` }}>
          <Icon size={20} style={{ color }} />
        </div>
      </div>
      <p className="text-2xl font-bold text-slate-800">{value}</p>
      <p className="text-sm font-medium text-slate-500 mt-0.5">{label}</p>
      {sub && <p className="text-xs text-slate-400 mt-1 truncate">{sub}</p>}
    </div>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();

  const [hoja, setHoja] = useState(null);
  const [resultado, setResultado] = useState(null);
  const [loading, setLoading] = useState(true);
  const [calculando, setCalculando] = useState(false);

  useEffect(() => { loadData(); }, []);

  useEffect(() => {
    let interval;
    if (hoja && (hoja.estado_procesamiento === 'PENDIENTE' || hoja.estado_procesamiento === 'PROCESANDO')) {
      interval = setInterval(async () => {
        try { 
          const res = await hojasAPI.miHoja(); 
          setHoja(res.data); 
          if (res.data.estado_procesamiento === 'COMPLETADO') {
             toast.success('¡Análisis de IA completado!');
          }
        } catch {}
      }, 3000);
    }
    return () => clearInterval(interval);
  }, [hoja?.estado_procesamiento]);

  const loadData = async () => {
    setLoading(true);
    try { const res = await hojasAPI.miHoja(); setHoja(res.data); } catch {}
    try { const res = await evaluacionAPI.resultado(); setResultado(res.data); } catch {}
    setLoading(false);
  };

  const handleCalcular = async () => {
    setCalculando(true);
    try {
      const res = await evaluacionAPI.calcular();
      setResultado(res.data);
      toast.success(`Puntaje calculado: ${res.data.puntaje_total.toFixed(1)} pts`);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al calcular');
    } finally {
      setCalculando(false);
    }
  };

  const currentStep = !hoja ? 0
    : hoja.estado_procesamiento === 'PENDIENTE' || hoja.estado_procesamiento === 'PROCESANDO' ? 1
    : hoja.estado_procesamiento === 'ERROR' ? 1
    : !resultado ? 2
    : 3;

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 size={28} className="animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
          ¡Hola, {user?.nombres}! <Sparkles size={22} className="text-amber-400" />
        </h1>
        <p className="text-slate-500 mt-1">
          {user?.estado ? `Estado de postulación: ${user.estado}` : 'Bienvenido a tu panel de evaluación docente.'}
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={FileText} label="Hoja de Vida" color="#3b82f6"
          value={hoja ? 'Cargada' : 'Pendiente'}
          sub={hoja ? hoja.nombre_archivo : 'Sube tu CV para comenzar'}
          onClick={!hoja ? () => navigate('/upload') : undefined}
        />
        <StatCard
          icon={Bot} label="Análisis IA" color="#8b5cf6"
          value={hoja ? hoja.estado_procesamiento : '—'}
          sub={hoja?.fecha_procesado ? `Procesado: ${new Date(hoja.fecha_procesado).toLocaleDateString()}` : 'Esperando CV'}
        />
        <StatCard
          icon={BarChart3} label="Puntaje Final" color="#10b981"
          value={resultado ? `${resultado.puntaje_total.toFixed(1)}` : '—'}
          sub={resultado ? `Calculado: ${new Date(resultado.fecha_calculo).toLocaleDateString()}` : 'Valida tus datos primero'}
          onClick={resultado ? () => navigate('/resultado') : undefined}
        />
        <StatCard
          icon={Award} label="Estado Admisión" color="#f59e0b"
          value={user?.estado || 'ENVIADO'}
          sub="Asignado por el comité"
        />
      </div>

      {/* Progress Steps */}
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
        <h2 className="text-base font-bold text-slate-800 mb-6">Tu Proceso de Postulación</h2>
        <div className="flex items-start relative">
          {/* Connecting line */}
          <div className="absolute top-5 left-5 right-5 h-0.5 bg-slate-100 z-0" />
          <div className="absolute top-5 left-5 h-0.5 bg-blue-600 z-0 transition-all duration-500" style={{ width: `${(currentStep / (STEPS.length - 1)) * 100}%`, maxWidth: 'calc(100% - 40px)' }} />

          {STEPS.map((s, i) => {
            const done = i < currentStep;
            const active = i === currentStep;
            const Icon = s.icon;
            return (
              <div key={s.key} className="flex-1 flex flex-col items-center relative z-10">
                <div className={`w-10 h-10 rounded-full flex items-center justify-center border-2 transition-all duration-300 ${
                  done ? 'bg-blue-600 border-blue-600 text-white' :
                  active ? 'bg-white border-blue-600 text-blue-600 shadow-md shadow-blue-500/20' :
                  'bg-white border-slate-200 text-slate-400'
                }`}>
                  {done ? <CheckSquare size={16} /> : <Icon size={16} />}
                </div>
                <p className={`text-xs font-semibold mt-2 ${active ? 'text-blue-600' : done ? 'text-slate-700' : 'text-slate-400'}`}>{s.label}</p>
                <p className="text-xs text-slate-400 mt-0.5 text-center hidden sm:block">{s.desc}</p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex flex-wrap gap-3">
        {!hoja && (
          <button onClick={() => navigate('/upload')} className="btn-primary flex items-center gap-2">
            <Upload size={18} /> Subir mi CV
          </button>
        )}
        {hoja?.estado_procesamiento === 'COMPLETADO' && (
          <button onClick={() => navigate('/validar')} className="btn-secondary flex items-center gap-2">
            <CheckSquare size={18} /> Revisar Datos IA
          </button>
        )}
        {hoja?.estado_procesamiento === 'COMPLETADO' && !resultado && (
          <button onClick={handleCalcular} disabled={calculando} className="btn-primary flex items-center gap-2">
            {calculando ? <Loader2 size={18} className="animate-spin" /> : <BarChart3 size={18} />}
            {calculando ? 'Calculando...' : 'Calcular Puntaje'}
          </button>
        )}
        {resultado && (
          <button onClick={() => navigate('/resultado')} className="btn-secondary flex items-center gap-2">
            <Trophy size={18} /> Ver Mi Resultado
          </button>
        )}
        {hoja && (
          <button onClick={() => navigate('/upload')} className="btn-secondary flex items-center gap-2">
            <RefreshCw size={18} /> Reemplazar CV
          </button>
        )}
      </div>

      {/* Processing status */}
      {hoja?.estado_procesamiento === 'PROCESANDO' && (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-5 flex items-center gap-4">
          <Loader2 size={22} className="animate-spin text-amber-600 shrink-0" />
          <div className="flex-1">
            <p className="font-semibold text-amber-800">La IA está analizando tu CV...</p>
            <p className="text-sm text-amber-600 mt-1">Gemini está extrayendo datos. Esto toma entre 10 y 30 segundos.</p>
          </div>
          <button onClick={loadData} className="btn-secondary text-sm py-2 px-4 flex items-center gap-1.5">
            <RefreshCw size={14} /> Actualizar
          </button>
        </div>
      )}

      {hoja?.estado_procesamiento === 'ERROR' && (
        <div className="bg-red-50 border border-red-200 rounded-2xl p-5 flex items-start gap-4">
          <AlertCircle size={22} className="text-red-500 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-red-800">Error al procesar tu CV</p>
            <p className="text-sm text-red-600 mt-1">Ocurrió un error durante el análisis. Por favor, elimina y vuelve a subir.</p>
            <button
              onClick={async () => {
                try { await hojasAPI.eliminar(hoja.id); setHoja(null); toast.success('CV eliminado'); }
                catch { toast.error('Error al eliminar'); }
              }}
              className="mt-3 text-sm font-semibold text-red-700 bg-red-100 px-4 py-2 rounded-xl hover:bg-red-200 transition"
            >
              Eliminar y subir de nuevo
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
