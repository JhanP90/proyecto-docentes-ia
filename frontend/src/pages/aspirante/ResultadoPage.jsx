// src/pages/aspirante/ResultadoPage.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useToast } from '../../contexts/ToastContext';
import { evaluacionAPI } from '../../api/client';
import { Trophy, BarChart3, Loader2, ArrowLeft, TrendingUp } from 'lucide-react';

const CATEGORY_LABELS = {
  FORMACION: { label: 'Formación Académica', color: '#3b82f6' },
  EXPERIENCIA: { label: 'Experiencia', color: '#8b5cf6' },
  PRODUCCION: { label: 'Producción Académica', color: '#10b981' },
  PONENCIAS: { label: 'Ponencias', color: '#f59e0b' },
  INVESTIGACION: { label: 'Investigación', color: '#ef4444' },
};

export default function ResultadoPage() {
  const navigate = useNavigate();
  const toast = useToast();

  const [resultado, setResultado] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    evaluacionAPI.resultado()
      .then((res) => setResultado(res.data))
      .catch((err) => {
        if (err.response?.status === 404) {
          toast.info('Aún no se ha calculado tu puntaje. Ve al panel principal.');
        } else {
          toast.error('Error al cargar resultado');
        }
        navigate('/dashboard');
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 size={28} className="animate-spin text-blue-600" />
      </div>
    );
  }

  if (!resultado) return null;

  const desglose = resultado.desglose_puntaje || {};
  const maxVal = Math.max(...Object.values(desglose), 1);

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button onClick={() => navigate('/dashboard')} className="p-2 rounded-xl hover:bg-slate-100 transition">
          <ArrowLeft size={20} className="text-slate-500" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Mi Resultado</h1>
          <p className="text-slate-500 text-sm">Desglose completo de tu evaluación docente</p>
        </div>
      </div>

      {/* Score card */}
      <div className="bg-gradient-to-br from-blue-600 via-indigo-600 to-blue-700 rounded-2xl p-8 text-white relative overflow-hidden shadow-xl">
        <div className="absolute top-0 right-0 w-60 h-60 bg-white/5 rounded-full -translate-y-1/2 translate-x-1/2" />
        <div className="absolute bottom-0 left-0 w-40 h-40 bg-white/5 rounded-full translate-y-1/2 -translate-x-1/2" />

        <div className="relative z-10 flex items-center justify-between">
          <div>
            <p className="text-blue-200 text-sm font-medium mb-1">Puntaje Total</p>
            <p className="text-5xl font-bold tracking-tight">{resultado.puntaje_total.toFixed(1)}</p>
            <p className="text-blue-200/80 text-sm mt-2">
              Calculado: {new Date(resultado.fecha_calculo).toLocaleDateString('es-CO', { year: 'numeric', month: 'long', day: 'numeric' })}
            </p>
          </div>
          <div className="w-20 h-20 bg-white/10 backdrop-blur rounded-2xl flex items-center justify-center border border-white/20">
            <Trophy size={36} className="text-white" />
          </div>
        </div>
      </div>

      {/* Breakdown */}
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
        <h2 className="text-base font-bold text-slate-800 mb-6 flex items-center gap-2">
          <BarChart3 size={18} className="text-blue-600" /> Desglose por Categoría
        </h2>
        <div className="space-y-5">
          {Object.entries(desglose).map(([key, value]) => {
            const config = CATEGORY_LABELS[key] || { label: key, color: '#64748b' };
            const pct = Math.min((value / maxVal) * 100, 100);
            return (
              <div key={key}>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-sm font-medium text-slate-700">{config.label}</span>
                  <span className="text-sm font-bold" style={{ color: config.color }}>{value.toFixed(1)} pts</span>
                </div>
                <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-700 ease-out"
                    style={{ width: `${pct}%`, backgroundColor: config.color }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Summary */}
      <div className="bg-emerald-50 border border-emerald-100 rounded-2xl p-5 flex items-start gap-4">
        <TrendingUp size={22} className="text-emerald-600 shrink-0 mt-0.5" />
        <div>
          <p className="font-semibold text-emerald-800">Evaluación Completa</p>
          <p className="text-sm text-emerald-700/80 mt-1">
            Tu puntaje ha sido calculado según las reglas vigentes. El comité de selección revisará tu perfil
            y actualizará tu estado de admisión.
          </p>
        </div>
      </div>

      <button onClick={() => navigate('/dashboard')} className="btn-secondary w-full py-3 flex items-center justify-center gap-2">
        <ArrowLeft size={18} /> Volver al Panel
      </button>
    </div>
  );
}
