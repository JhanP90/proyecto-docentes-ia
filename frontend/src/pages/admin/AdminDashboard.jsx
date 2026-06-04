// src/pages/admin/AdminDashboard.jsx
import React, { useState, useEffect } from 'react';
import { useToast } from '../../contexts/ToastContext';
import { adminAPI } from '../../api/client';
import {
  Users, Loader2, CheckCircle, XCircle, Clock, Search, Filter,
  ChevronLeft, ChevronRight, Award, FileText
} from 'lucide-react';

const ESTADO_BADGE = {
  ENVIADO: { bg: 'bg-slate-100', text: 'text-slate-700', label: 'Enviado' },
  EN_PROCESO: { bg: 'bg-amber-100', text: 'text-amber-800', label: 'En Proceso' },
  EVALUADO: { bg: 'bg-blue-100', text: 'text-blue-800', label: 'Evaluado' },
  ACEPTADO: { bg: 'bg-emerald-100', text: 'text-emerald-800', label: 'Aceptado' },
  RECHAZADO: { bg: 'bg-red-100', text: 'text-red-800', label: 'Rechazado' },
};

export default function AdminDashboard() {
  const toast = useToast();
  const [ranking, setRanking] = useState([]);
  const [total, setTotal] = useState(0);
  const [pagina, setPagina] = useState(1);
  const [loading, setLoading] = useState(true);
  const [filtroEstado, setFiltroEstado] = useState('');
  const [busqueda, setBusqueda] = useState('');
  const porPagina = 10;

  useEffect(() => { cargarRanking(); }, [pagina, filtroEstado]);

  const cargarRanking = async () => {
    setLoading(true);
    try {
      const params = { pagina, por_pagina: porPagina };
      if (filtroEstado) params.estado = filtroEstado;
      const { data } = await adminAPI.getRanking(params);
      setRanking(data.items || []);
      setTotal(data.total || 0);
    } catch (err) {
      toast.error('Error al cargar el ranking');
    } finally {
      setLoading(false);
    }
  };

  const handleEstado = async (aspiranteId, estado) => {
    try {
      await adminAPI.cambiarEstado(aspiranteId, estado);
      toast.success(`Estado actualizado a ${estado}`);
      cargarRanking();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al cambiar estado');
    }
  };

  const totalPages = Math.ceil(total / porPagina);

  const filteredRanking = busqueda
    ? ranking.filter((a) =>
        `${a.nombres} ${a.apellidos} ${a.cedula} ${a.email}`.toLowerCase().includes(busqueda.toLowerCase())
      )
    : ranking;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
          <Users size={24} className="text-blue-600" /> Gestión de Postulantes
        </h1>
        <p className="text-slate-500 mt-1">Ranking de aspirantes docentes ordenado por puntaje.</p>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            placeholder="Buscar por nombre, cédula o email..."
            className="input-field pl-11"
          />
        </div>
        <div className="relative">
          <Filter size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <select
            value={filtroEstado}
            onChange={(e) => { setFiltroEstado(e.target.value); setPagina(1); }}
            className="input-field pl-11 pr-10 appearance-none cursor-pointer min-w-[180px]"
          >
            <option value="">Todos los estados</option>
            <option value="ENVIADO">Enviado</option>
            <option value="EN_PROCESO">En Proceso</option>
            <option value="EVALUADO">Evaluado</option>
            <option value="ACEPTADO">Aceptados</option>
            <option value="RECHAZADO">Rechazados</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 size={28} className="animate-spin text-blue-600" />
          </div>
        ) : filteredRanking.length === 0 ? (
          <div className="text-center py-16 text-slate-400">
            <Users size={40} className="mx-auto mb-3 opacity-40" />
            <p className="font-medium">No hay postulantes registrados</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="bg-slate-50 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                <tr>
                  <th className="px-6 py-4">#</th>
                  <th className="px-6 py-4">Aspirante</th>
                  <th className="px-6 py-4">Cédula</th>
                  <th className="px-6 py-4">CV</th>
                  <th className="px-6 py-4 text-center">Puntaje</th>
                  <th className="px-6 py-4">Estado</th>
                  <th className="px-6 py-4 text-center">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50 text-sm">
                {filteredRanking.map((asp, idx) => {
                  const badge = ESTADO_BADGE[asp.estado] || ESTADO_BADGE.EN_REVISION;
                  return (
                    <tr key={asp.id} className="hover:bg-slate-50/50 transition">
                      <td className="px-6 py-4 text-slate-400 font-medium">{(pagina - 1) * porPagina + idx + 1}</td>
                      <td className="px-6 py-4">
                        <p className="font-semibold text-slate-800">{asp.nombres} {asp.apellidos}</p>
                        <p className="text-xs text-slate-400 mt-0.5">{asp.email}</p>
                      </td>
                      <td className="px-6 py-4 text-slate-600 font-mono text-xs">{asp.cedula}</td>
                      <td className="px-6 py-4">
                        {asp.hoja_vida_estado ? (
                          <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-full ${
                            asp.hoja_vida_estado === 'COMPLETADO' ? 'bg-emerald-50 text-emerald-700' :
                            asp.hoja_vida_estado === 'PROCESANDO' ? 'bg-amber-50 text-amber-700' :
                            asp.hoja_vida_estado === 'ERROR' ? 'bg-red-50 text-red-700' :
                            'bg-slate-50 text-slate-500'
                          }`}>
                            <FileText size={12} /> {asp.hoja_vida_estado}
                          </span>
                        ) : <span className="text-xs text-slate-400">—</span>}
                      </td>
                      <td className="px-6 py-4 text-center">
                        {asp.puntaje_total != null ? (
                          <span className="text-lg font-bold text-blue-700">{asp.puntaje_total.toFixed(1)}</span>
                        ) : <span className="text-slate-400">—</span>}
                      </td>
                      <td className="px-6 py-4">
                        <span className={`inline-block text-xs font-bold px-2.5 py-1 rounded-full ${badge.bg} ${badge.text}`}>
                          {badge.label}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-center">
                        <div className="flex items-center justify-center gap-1.5">
                          {asp.estado !== 'ACEPTADO' && (
                            <button
                              onClick={() => handleEstado(asp.id, 'ACEPTADO')}
                              title="Aceptar"
                              className="p-1.5 rounded-lg text-emerald-600 hover:bg-emerald-50 transition"
                            >
                              <CheckCircle size={18} />
                            </button>
                          )}
                          {asp.estado !== 'RECHAZADO' && (
                            <button
                              onClick={() => handleEstado(asp.id, 'RECHAZADO')}
                              title="Rechazar"
                              className="p-1.5 rounded-lg text-red-500 hover:bg-red-50 transition"
                            >
                              <XCircle size={18} />
                            </button>
                          )}
                          {asp.estado !== 'EN_PROCESO' && (
                            <button
                              onClick={() => handleEstado(asp.id, 'EN_PROCESO')}
                              title="En Proceso"
                              className="p-1.5 rounded-lg text-amber-500 hover:bg-amber-50 transition"
                            >
                              <Clock size={18} />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-6 py-4 border-t border-slate-100 bg-slate-50/50">
            <p className="text-sm text-slate-500">
              Mostrando {(pagina - 1) * porPagina + 1}–{Math.min(pagina * porPagina, total)} de {total}
            </p>
            <div className="flex items-center gap-2">
              <button
                disabled={pagina <= 1}
                onClick={() => setPagina((p) => p - 1)}
                className="p-2 rounded-lg hover:bg-white border border-slate-200 disabled:opacity-40 transition"
              >
                <ChevronLeft size={16} />
              </button>
              <span className="text-sm font-medium text-slate-600 px-2">{pagina} / {totalPages}</span>
              <button
                disabled={pagina >= totalPages}
                onClick={() => setPagina((p) => p + 1)}
                className="p-2 rounded-lg hover:bg-white border border-slate-200 disabled:opacity-40 transition"
              >
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
