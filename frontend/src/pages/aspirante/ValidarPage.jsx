// src/pages/aspirante/ValidarPage.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useToast } from '../../contexts/ToastContext';
import { hojasAPI } from '../../api/client';
import {
  Loader2, CheckCircle, AlertTriangle, GraduationCap, Briefcase,
  BookOpen, Mic, FlaskConical, Save, ChevronDown, ChevronUp, Eye, Pencil
} from 'lucide-react';

const SECTION_CONFIG = {
  titulos_academicos: {
    icon: GraduationCap, color: 'blue', label: 'Títulos Académicos',
    fields: ['nivel', 'nombre_titulo', 'institucion', 'año_graduacion', 'pais'],
    labels: { nivel: 'Nivel', nombre_titulo: 'Título', institucion: 'Institución', año_graduacion: 'Año', pais: 'País' },
  },
  experiencia_laboral: {
    icon: Briefcase, color: 'indigo', label: 'Experiencia Laboral',
    fields: ['cargo', 'institucion', 'tipo', 'fecha_inicio', 'fecha_fin', 'años_calculados'],
    labels: { cargo: 'Cargo', institucion: 'Institución', tipo: 'Tipo', fecha_inicio: 'Inicio', fecha_fin: 'Fin', años_calculados: 'Años' },
  },
  publicaciones: {
    icon: BookOpen, color: 'purple', label: 'Publicaciones',
    fields: ['tipo', 'titulo', 'revista_o_editorial', 'año'],
    labels: { tipo: 'Tipo', titulo: 'Título', revista_o_editorial: 'Revista/Editorial', año: 'Año' },
  },
  ponencias: {
    icon: Mic, color: 'amber', label: 'Ponencias',
    fields: ['titulo', 'evento', 'tipo', 'año', 'pais'],
    labels: { titulo: 'Título', evento: 'Evento', tipo: 'Tipo', año: 'Año', pais: 'País' },
  },
  proyectos_investigacion: {
    icon: FlaskConical, color: 'emerald', label: 'Proyectos de Investigación',
    fields: ['titulo', 'rol', 'entidad_financiadora', 'año_inicio', 'año_fin'],
    labels: { titulo: 'Título', rol: 'Rol', entidad_financiadora: 'Financiador', año_inicio: 'Inicio', año_fin: 'Fin' },
  },
};

function Section({ sectionKey, items, onChange, config }) {
  const [expanded, setExpanded] = useState(true);
  const Icon = config.icon;

  const handleFieldChange = (idx, field, value) => {
    const updated = items.map((item, i) => i === idx ? { ...item, [field]: value } : item);
    onChange(sectionKey, updated);
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-5 py-4 hover:bg-slate-50 transition text-left"
      >
        <div className={`w-9 h-9 rounded-xl flex items-center justify-center bg-${config.color}-50`}>
          <Icon size={18} className={`text-${config.color}-600`} />
        </div>
        <div className="flex-1">
          <h3 className="font-semibold text-slate-800">{config.label}</h3>
          <p className="text-xs text-slate-400">{items.length} elemento(s) detectado(s)</p>
        </div>
        {expanded ? <ChevronUp size={18} className="text-slate-400" /> : <ChevronDown size={18} className="text-slate-400" />}
      </button>

      {expanded && (
        <div className="px-5 pb-5 space-y-4">
          {items.length === 0 ? (
            <p className="text-sm text-slate-400 italic py-3">No se detectaron elementos en esta sección.</p>
          ) : (
            items.map((item, idx) => (
              <div key={idx} className="bg-slate-50 rounded-xl p-4 border border-slate-100">
                <p className="text-xs font-bold text-slate-400 uppercase mb-3">#{idx + 1}</p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {config.fields.map((field) => (
                    <div key={field}>
                      <label className="block text-xs font-semibold text-slate-500 mb-1">{config.labels[field]}</label>
                      <input
                        type="text"
                        value={item[field] ?? ''}
                        onChange={(e) => handleFieldChange(idx, field, e.target.value)}
                        className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-400/10 transition"
                      />
                    </div>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

export default function ValidarPage() {
  const navigate = useNavigate();
  const toast = useToast();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [hoja, setHoja] = useState(null);
  const [datos, setDatos] = useState(null);
  const [editData, setEditData] = useState(null);
  const [confianza, setConfianza] = useState(0);
  const [observaciones, setObservaciones] = useState('');

  useEffect(() => { loadDatos(); }, []);

  const loadDatos = async () => {
    setLoading(true);
    try {
      const hojaRes = await hojasAPI.miHoja();
      setHoja(hojaRes.data);
      const datosRes = await hojasAPI.datosIA(hojaRes.data.id);
      setDatos(datosRes.data);
      const source = datosRes.data.json_validado || datosRes.data.json_estructurado;
      setEditData({ ...source });
      setConfianza(source.confianza_extraccion || 0);
      setObservaciones(source.observaciones_ia || '');
    } catch (err) {
      if (err.response?.status === 404) {
        toast.warning('Primero debes subir tu hoja de vida.');
        navigate('/upload');
      } else if (err.response?.status === 425) {
        toast.info('La IA aún está procesando tu CV. Intenta en unos momentos.');
        navigate('/dashboard');
      } else {
        toast.error(err.response?.data?.detail || 'Error al cargar datos');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSectionChange = (key, updated) => {
    setEditData((prev) => ({ ...prev, [key]: updated }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await hojasAPI.validar(hoja.id, { datos_corregidos: editData });
      toast.success('Datos validados correctamente. Ya puedes calcular tu puntaje.');
      navigate('/dashboard');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al validar');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 size={28} className="animate-spin text-blue-600" />
      </div>
    );
  }

  if (!editData) return null;

  const confianzaPct = Math.round(confianza * 100);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            <Pencil size={22} className="text-blue-600" /> Validar Datos Extraídos
          </h1>
          <p className="text-slate-500 mt-1">Revisa y corrige la información que la IA extrajo de tu CV.</p>
        </div>
        <button onClick={handleSave} disabled={saving} className="btn-primary flex items-center gap-2">
          {saving ? <Loader2 size={18} className="animate-spin" /> : <Save size={18} />}
          {saving ? 'Guardando...' : 'Confirmar y Guardar'}
        </button>
      </div>

      {/* Confidence bar */}
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-semibold text-slate-700">Confianza de la IA</span>
          <span className={`text-sm font-bold ${confianzaPct >= 80 ? 'text-emerald-600' : confianzaPct >= 50 ? 'text-amber-600' : 'text-red-600'}`}>
            {confianzaPct}%
          </span>
        </div>
        <div className="w-full h-2.5 bg-slate-100 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-700 ${
              confianzaPct >= 80 ? 'bg-emerald-500' : confianzaPct >= 50 ? 'bg-amber-500' : 'bg-red-500'
            }`}
            style={{ width: `${confianzaPct}%` }}
          />
        </div>
        {observaciones && (
          <div className="mt-3 flex items-start gap-2 text-sm text-slate-500 bg-slate-50 rounded-xl p-3">
            <AlertTriangle size={16} className="text-amber-500 shrink-0 mt-0.5" />
            <p>{observaciones}</p>
          </div>
        )}
      </div>

      {/* Personal info */}
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5">
        <h3 className="font-semibold text-slate-700 mb-3 flex items-center gap-2">
          <Eye size={16} className="text-slate-400" /> Datos Personales Detectados
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {[
            ['Nombre', editData.nombre_completo],
            ['Cédula', editData.cedula_detectada],
            ['Email', editData.email_detectado],
            ['Teléfono', editData.telefono_detectado],
          ].map(([label, val]) => (
            <div key={label} className="flex items-center gap-2 bg-slate-50 rounded-lg px-3 py-2">
              <span className="text-xs font-semibold text-slate-400 w-16 shrink-0">{label}</span>
              <span className="text-sm text-slate-700 truncate">{val || '—'}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Editable Sections */}
      {Object.entries(SECTION_CONFIG).map(([key, config]) => (
        <Section
          key={key}
          sectionKey={key}
          items={editData[key] || []}
          onChange={handleSectionChange}
          config={config}
        />
      ))}

      {/* Bottom save */}
      <div className="flex justify-end gap-3 pt-4">
        <button onClick={() => navigate('/dashboard')} className="btn-secondary py-3 px-6">
          Cancelar
        </button>
        <button onClick={handleSave} disabled={saving} className="btn-primary py-3 px-8 flex items-center gap-2">
          {saving ? <Loader2 size={18} className="animate-spin" /> : <CheckCircle size={18} />}
          {saving ? 'Guardando...' : 'Confirmar Datos'}
        </button>
      </div>
    </div>
  );
}
