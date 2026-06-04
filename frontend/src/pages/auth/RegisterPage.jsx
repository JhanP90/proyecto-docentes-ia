// src/pages/auth/RegisterPage.jsx
import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useToast } from '../../contexts/ToastContext';
import { GraduationCap, User, Mail, Lock, Phone, MapPin, FileText, Loader2, ArrowRight, ArrowLeft } from 'lucide-react';

// ⚠️ IMPORTANTE: Este componente DEBE estar fuera de RegisterPage
// Si se define dentro, React lo recrea en cada render y el input pierde el foco
const DEPARTAMENTOS_COLOMBIA = [
  'Amazonas', 'Antioquia', 'Arauca', 'Atlántico', 'Bogotá D.C.', 'Bolívar', 'Boyacá', 
  'Caldas', 'Caquetá', 'Casanare', 'Cauca', 'Cesar', 'Chocó', 'Córdoba', 'Cundinamarca', 
  'Guainía', 'Guaviare', 'Huila', 'La Guajira', 'Magdalena', 'Meta', 'Nariño', 
  'Norte de Santander', 'Putumayo', 'Quindío', 'Risaralda', 'San Andrés y Providencia', 
  'Santander', 'Sucre', 'Tolima', 'Valle del Cauca', 'Vaupés', 'Vichada'
];

function InputField({ name, label, icon: Icon, type = 'text', placeholder, value, onChange, error, ...rest }) {
  return (
    <div>
      <label htmlFor={name} className="block text-sm font-semibold text-slate-700 mb-1.5">{label}</label>
      <div className="relative">
        <Icon size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
        <input
          id={name}
          name={name}
          type={type}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          className={`input-field pl-11 ${error ? 'border-red-400' : ''}`}
          {...rest}
        />
      </div>
      {error && <p className="text-xs text-red-500 mt-1">{error}</p>}
    </div>
  );
}

function SelectField({ name, label, icon: Icon, options, value, onChange, error, placeholder }) {
  return (
    <div>
      <label htmlFor={name} className="block text-sm font-semibold text-slate-700 mb-1.5">{label}</label>
      <div className="relative">
        <Icon size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
        <select
          id={name}
          name={name}
          value={value}
          onChange={onChange}
          className={`input-field pl-11 appearance-none bg-no-repeat cursor-pointer ${error ? 'border-red-400' : ''}`}
          style={{ backgroundImage: 'url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns=\'http://www.w3.org/2000/svg\' viewBox=\'0 0 24 24\' fill=\'none\' stroke=\'%2394a3b8\' stroke-width=\'2\' stroke-linecap=\'round\' stroke-linejoin=\'round\'%3e%3cpolyline points=\'6 9 12 15 18 9\'%3e%3c/polyline%3e%3c/svg%3e")', backgroundPosition: 'right 1rem center', backgroundSize: '1em' }}
        >
          <option value="" disabled hidden>{placeholder}</option>
          {options.map(opt => <option key={opt} value={opt}>{opt}</option>)}
        </select>
      </div>
      {error && <p className="text-xs text-red-500 mt-1">{error}</p>}
    </div>
  );
}

export default function RegisterPage() {
  const navigate = useNavigate();
  const { register } = useAuth();
  const toast = useToast();

  const [form, setForm] = useState({
    nombres: '', apellidos: '', email: '', password: '', confirmPassword: '',
    cedula: '', pais: 'Colombia', departamento: '', municipio: '', telefono: '',
  });
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});
  const [step, setStep] = useState(1);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    if (errors[name]) setErrors((prev) => ({ ...prev, [name]: '' }));
  };

  const validateStep1 = () => {
    const errs = {};
    if (!form.nombres.trim()) errs.nombres = 'Requerido';
    if (!form.apellidos.trim()) errs.apellidos = 'Requerido';
    if (!form.email.trim()) errs.email = 'Requerido';
    if (!form.cedula.trim()) errs.cedula = 'Requerido';
    else if (!/^\d{5,20}$/.test(form.cedula)) errs.cedula = 'Solo dígitos (5-20)';
    return errs;
  };

  const validateStep2 = () => {
    const errs = {};
    if (!form.departamento.trim()) errs.departamento = 'Requerido';
    if (!form.municipio.trim()) errs.municipio = 'Requerido';
    if (!form.password) errs.password = 'Requerido';
    else if (form.password.length < 8) errs.password = 'Mínimo 8 caracteres';
    if (form.password !== form.confirmPassword) errs.confirmPassword = 'Las contraseñas no coinciden';
    return errs;
  };

  const nextStep = () => {
    const errs = validateStep1();
    if (Object.keys(errs).length) { setErrors(errs); return; }
    setStep(2);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const errs = validateStep2();
    if (Object.keys(errs).length) { setErrors(errs); return; }

    setLoading(true);
    try {
      const { confirmPassword, ...payload } = form;
      await register(payload);
      toast.success('¡Registro exitoso! Ahora inicia sesión.');
      navigate('/login');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al registrar');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
      <div className="w-full max-w-lg slide-up">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-xl flex items-center justify-center shadow">
            <GraduationCap size={20} className="text-white" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-800">Registro de Aspirante</h2>
            <p className="text-sm text-slate-500">Universidad de Caldas</p>
          </div>
        </div>

        {/* Step indicator */}
        <div className="flex items-center gap-3 mb-8">
          {[1, 2].map((s) => (
            <React.Fragment key={s}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-all ${
                step >= s ? 'bg-blue-600 text-white shadow-md shadow-blue-500/30' : 'bg-slate-200 text-slate-500'
              }`}>{s}</div>
              {s < 2 && <div className={`flex-1 h-0.5 rounded-full transition-all ${step >= 2 ? 'bg-blue-600' : 'bg-slate-200'}`} />}
            </React.Fragment>
          ))}
        </div>

        <div className="bg-white rounded-2xl shadow-lg border border-slate-100 p-6 lg:p-8">
          <form onSubmit={handleSubmit}>
            {step === 1 && (
              <div className="space-y-4 fade-in">
                <h3 className="text-lg font-bold text-slate-800 mb-4">Datos Personales</h3>
                <div className="grid grid-cols-2 gap-4">
                  <InputField name="nombres" label="Nombres" icon={User} placeholder="Juan Carlos" value={form.nombres} onChange={handleChange} error={errors.nombres} />
                  <InputField name="apellidos" label="Apellidos" icon={User} placeholder="Pérez López" value={form.apellidos} onChange={handleChange} error={errors.apellidos} />
                </div>
                <InputField name="email" label="Correo Electrónico" icon={Mail} type="email" placeholder="correo@ejemplo.com" value={form.email} onChange={handleChange} error={errors.email} />
                <InputField name="cedula" label="Cédula de Ciudadanía" icon={FileText} placeholder="1023456789" value={form.cedula} onChange={handleChange} error={errors.cedula} />
                <InputField name="telefono" label="Teléfono (opcional)" icon={Phone} placeholder="3001234567" value={form.telefono} onChange={handleChange} error={errors.telefono} />
                <button type="button" onClick={nextStep} className="btn-primary w-full flex items-center justify-center gap-2 py-3 mt-2">
                  Continuar <ArrowRight size={18} />
                </button>
              </div>
            )}

            {step === 2 && (
              <div className="space-y-4 fade-in">
                <h3 className="text-lg font-bold text-slate-800 mb-4">Ubicación y Contraseña</h3>
                <SelectField name="departamento" label="Departamento" icon={MapPin} options={DEPARTAMENTOS_COLOMBIA} placeholder="Selecciona un departamento" value={form.departamento} onChange={handleChange} error={errors.departamento} />
                <InputField name="municipio" label="Municipio" icon={MapPin} placeholder="Manizales" value={form.municipio} onChange={handleChange} error={errors.municipio} />
                <InputField name="password" label="Contraseña" icon={Lock} type="password" placeholder="Mínimo 8 caracteres" value={form.password} onChange={handleChange} error={errors.password} />
                <InputField name="confirmPassword" label="Confirmar Contraseña" icon={Lock} type="password" placeholder="Repite tu contraseña" value={form.confirmPassword} onChange={handleChange} error={errors.confirmPassword} />
                <div className="flex gap-3 mt-2">
                  <button type="button" onClick={() => setStep(1)} className="btn-secondary flex items-center gap-2 flex-1 justify-center py-3">
                    <ArrowLeft size={18} /> Atrás
                  </button>
                  <button type="submit" disabled={loading} className="btn-primary flex items-center gap-2 flex-1 justify-center py-3">
                    {loading ? <><Loader2 size={18} className="animate-spin" /> Registrando...</> : <>Crear Cuenta <ArrowRight size={18} /></>}
                  </button>
                </div>
              </div>
            )}
          </form>
        </div>

        <p className="text-center text-sm text-slate-500 mt-6">
          ¿Ya tienes cuenta?{' '}
          <Link to="/login" className="text-blue-600 hover:text-blue-700 font-semibold">Inicia Sesión</Link>
        </p>
      </div>
    </div>
  );
}
