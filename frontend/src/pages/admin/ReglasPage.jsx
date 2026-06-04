// src/pages/admin/ReglasPage.jsx
import React, { useState, useEffect } from 'react';
import { useToast } from '../../contexts/ToastContext';
import { adminAPI } from '../../api/client';
import {
  Settings, Loader2, Save, Edit2, X, Check,
  GraduationCap, Briefcase, BookOpen, Mic, FlaskConical
} from 'lucide-react';

const CATEGORY_UI = {
  FORMACION: { icon: GraduationCap, color: 'blue', label: 'Formación Académica' },
  EXPERIENCIA: { icon: Briefcase, color: 'indigo', label: 'Experiencia' },
  PRODUCCION: { icon: BookOpen, color: 'purple', label: 'Producción Académica' },
  PONENCIAS: { icon: Mic, color: 'amber', label: 'Ponencias' },
  INVESTIGACION: { icon: FlaskConical, color: 'emerald', label: 'Investigación' },
};

export default function ReglasPage() {
  const toast = useToast();
  const [reglas, setReglas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editId, setEditId] = useState(null);
  const [editBuf, setEditBuf] = useState({});
  const [saving, setSaving] = useState(false);

  useEffect(() => { cargarReglas(); }, []);

  const cargarReglas = async () => {
    setLoading(true);
    try {
      const { data } = await adminAPI.getReglas();
      setReglas(data);
    } catch {
      toast.error('Error al cargar reglas');
    } finally {
      setLoading(false);
    }
  };

  const startEdit = (regla) => {
    setEditId(regla.id);
    setEditBuf({ puntos_por_item: regla.puntos_por_item, tope_maximo_categoria: regla.tope_maximo_categoria });
  };

  const cancelEdit = () => { setEditId(null); setEditBuf({}); };

  const saveEdit = async () => {
    setSaving(true);
    try {
      await adminAPI.updateRegla(editId, editBuf);
      toast.success('Regla actualizada');
      setEditId(null);
      cargarReglas();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al guardar');
    } finally {
      setSaving(false);
    }
  };

  // Group rules by category
  const grouped = reglas.reduce((acc, r) => {
    if (!acc[r.categoria]) acc[r.categoria] = [];
    acc[r.categoria].push(r);
    return acc;
  }, {});

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 size={28} className="animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
          <Settings size={24} className="text-blue-600" /> Motor de Reglas
        </h1>
        <p className="text-slate-500 mt-1">Configura los pesos y topes de evaluación para cada categoría.</p>
      </div>

      {Object.entries(grouped).map(([cat, items]) => {
        const ui = CATEGORY_UI[cat] || { icon: Settings, color: 'slate', label: cat };
        const Icon = ui.icon;

        return (
          <div key={cat} className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
            {/* Category header */}
            <div className={`px-6 py-4 flex items-center gap-3 border-b border-slate-100 bg-${ui.color}-50/30`}>
              <div className={`w-9 h-9 rounded-xl flex items-center justify-center bg-${ui.color}-100`}>
                <Icon size={18} className={`text-${ui.color}-600`} />
              </div>
              <div>
                <h2 className="font-bold text-slate-800">{ui.label}</h2>
                <p className="text-xs text-slate-400">{items.length} regla(s)</p>
              </div>
            </div>

            {/* Rules table */}
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead className="text-xs font-semibold text-slate-400 uppercase bg-slate-50/50">
                  <tr>
                    <th className="px-6 py-3">Ítem</th>
                    <th className="px-6 py-3">Unidad</th>
                    <th className="px-6 py-3 text-center">Pts/Ítem</th>
                    <th className="px-6 py-3 text-center">Tope Máx.</th>
                    <th className="px-6 py-3 text-center w-24">Acción</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50 text-sm">
                  {items.map((regla) => {
                    const isEditing = editId === regla.id;
                    return (
                      <tr key={regla.id} className={`transition ${isEditing ? 'bg-blue-50/30' : 'hover:bg-slate-50/50'}`}>
                        <td className="px-6 py-3.5">
                          <p className="font-medium text-slate-700">{regla.nombre_item}</p>
                          {regla.descripcion && <p className="text-xs text-slate-400 mt-0.5">{regla.descripcion}</p>}
                        </td>
                        <td className="px-6 py-3.5 text-slate-500 text-xs">{regla.unidad || '—'}</td>
                        <td className="px-6 py-3.5 text-center">
                          {isEditing ? (
                            <input
                              type="number"
                              step="0.5"
                              value={editBuf.puntos_por_item}
                              onChange={(e) => setEditBuf((b) => ({ ...b, puntos_por_item: parseFloat(e.target.value) || 0 }))}
                              className="w-20 mx-auto text-center border-2 border-blue-300 rounded-lg py-1.5 text-sm font-bold text-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-400/20"
                            />
                          ) : (
                            <span className="inline-block font-bold text-blue-700 bg-blue-50 px-3 py-1 rounded-lg">{regla.puntos_por_item}</span>
                          )}
                        </td>
                        <td className="px-6 py-3.5 text-center">
                          {isEditing ? (
                            <input
                              type="number"
                              step="0.5"
                              value={editBuf.tope_maximo_categoria}
                              onChange={(e) => setEditBuf((b) => ({ ...b, tope_maximo_categoria: parseFloat(e.target.value) || 0 }))}
                              className="w-20 mx-auto text-center border-2 border-slate-300 rounded-lg py-1.5 text-sm font-bold text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-400/20"
                            />
                          ) : (
                            <span className="inline-block font-semibold text-slate-600 bg-slate-100 px-3 py-1 rounded-lg">{regla.tope_maximo_categoria}</span>
                          )}
                        </td>
                        <td className="px-6 py-3.5 text-center">
                          {isEditing ? (
                            <div className="flex items-center justify-center gap-1">
                              <button
                                onClick={saveEdit}
                                disabled={saving}
                                className="p-1.5 rounded-lg text-emerald-600 hover:bg-emerald-50 transition"
                              >
                                {saving ? <Loader2 size={16} className="animate-spin" /> : <Check size={16} />}
                              </button>
                              <button onClick={cancelEdit} className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 transition">
                                <X size={16} />
                              </button>
                            </div>
                          ) : (
                            <button onClick={() => startEdit(regla)} className="p-1.5 rounded-lg text-slate-400 hover:text-blue-600 hover:bg-blue-50 transition">
                              <Edit2 size={16} />
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        );
      })}
    </div>
  );
}
