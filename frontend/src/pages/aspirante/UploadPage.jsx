// src/pages/aspirante/UploadPage.jsx
import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useToast } from '../../contexts/ToastContext';
import { hojasAPI } from '../../api/client';
import { Upload, FileText, X, Loader2, CheckCircle, CloudUpload } from 'lucide-react';

export default function UploadPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const inputRef = useRef(null);

  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const handleFile = (f) => {
    if (!f) return;
    if (!f.name.toLowerCase().endsWith('.pdf')) {
      toast.error('Solo se aceptan archivos PDF');
      return;
    }
    if (f.size > 10 * 1024 * 1024) {
      toast.error('El archivo no puede superar los 10 MB');
      return;
    }
    setFile(f);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    handleFile(e.dataTransfer.files?.[0]);
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    try {
      await hojasAPI.upload(file);
      toast.success('Hoja de vida subida correctamente. La IA está procesando tu CV...');
      navigate('/dashboard');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al subir el archivo');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Subir Hoja de Vida</h1>
        <p className="text-slate-500 mt-1">Carga tu CV en formato PDF. La IA extraerá automáticamente tus datos académicos y laborales.</p>
      </div>

      {/* Drop Zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={`relative border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all duration-300 ${
          dragOver
            ? 'border-blue-500 bg-blue-50 scale-[1.01]'
            : file
              ? 'border-emerald-300 bg-emerald-50/50'
              : 'border-slate-200 bg-white hover:border-blue-300 hover:bg-blue-50/30'
        }`}
      >
        <input ref={inputRef} type="file" accept=".pdf" className="hidden" onChange={(e) => handleFile(e.target.files?.[0])} />

        {file ? (
          <div className="flex flex-col items-center gap-3">
            <div className="w-16 h-16 bg-emerald-100 rounded-2xl flex items-center justify-center">
              <FileText size={28} className="text-emerald-600" />
            </div>
            <div>
              <p className="font-semibold text-slate-800">{file.name}</p>
              <p className="text-sm text-slate-500">{(file.size / (1024 * 1024)).toFixed(2)} MB</p>
            </div>
            <button
              onClick={(e) => { e.stopPropagation(); setFile(null); }}
              className="text-xs text-red-500 hover:text-red-700 flex items-center gap-1 mt-1"
            >
              <X size={14} /> Quitar archivo
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <div className="w-16 h-16 bg-blue-50 rounded-2xl flex items-center justify-center">
              <CloudUpload size={28} className="text-blue-500" />
            </div>
            <div>
              <p className="font-semibold text-slate-700">Arrastra tu PDF aquí</p>
              <p className="text-sm text-slate-400 mt-1">o haz clic para seleccionar un archivo</p>
            </div>
            <span className="text-xs text-slate-400 bg-slate-100 px-3 py-1 rounded-full">PDF • Máximo 10 MB</span>
          </div>
        )}
      </div>

      {/* Upload button */}
      <div className="flex gap-3">
        <button onClick={() => navigate('/dashboard')} className="btn-secondary flex-1 py-3 flex items-center justify-center gap-2">
          Cancelar
        </button>
        <button
          onClick={handleUpload}
          disabled={!file || uploading}
          className="btn-primary flex-1 py-3 flex items-center justify-center gap-2"
        >
          {uploading ? (
            <><Loader2 size={18} className="animate-spin" /> Subiendo...</>
          ) : (
            <><Upload size={18} /> Subir Hoja de Vida</>
          )}
        </button>
      </div>

      {/* Info */}
      <div className="bg-blue-50 border border-blue-100 rounded-2xl p-5">
        <h3 className="font-semibold text-blue-800 mb-2 text-sm">¿Qué pasa después?</h3>
        <ul className="text-sm text-blue-700/80 space-y-1.5">
          <li className="flex items-start gap-2"><CheckCircle size={14} className="mt-0.5 shrink-0 text-blue-500" /> La IA analizará tu hoja de vida automáticamente.</li>
          <li className="flex items-start gap-2"><CheckCircle size={14} className="mt-0.5 shrink-0 text-blue-500" /> Se extraerán títulos, experiencia, publicaciones y ponencias.</li>
          <li className="flex items-start gap-2"><CheckCircle size={14} className="mt-0.5 shrink-0 text-blue-500" /> Podrás revisar y corregir los datos antes de calcular tu puntaje.</li>
        </ul>
      </div>
    </div>
  );
}
