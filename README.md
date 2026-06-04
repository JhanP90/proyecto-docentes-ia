# Sistema de Evaluación Docente con IA

Aplicación full-stack que automatiza la evaluación de hojas de vida (CVs) de aspirantes a docentes de la Universidad de Caldas usando Inteligencia Artificial (Google Gemini).

## Arquitectura
- **Frontend:** React + Vite + Tailwind CSS.
- **Backend:** Python + FastAPI + SQLAlchemy.
- **Base de Datos:** SQLite (por defecto para entorno local) / PostgreSQL.
- **IA:** Google Gemini (1.5 Flash / 1.5 Pro).

---

## 🚀 Guía de Instalación (Entorno Local)

Para que cualquier persona pueda correr este proyecto fácilmente en su computadora, solo debe seguir estos 3 pasos:

### 1. Requisitos Previos
Asegúrate de tener instalado en tu computadora:
- [Node.js](https://nodejs.org/es/) (Versión 18 o superior)
- [Python](https://www.python.org/downloads/) (Versión 3.9 o superior)

### 2. Configurar el Entorno

En la carpeta raíz del proyecto, debes configurar el archivo oculto `.env` para el backend. 
1. Ve a la carpeta `backend/`.
2. Busca el archivo `.env.example` y duplícalo (cópialo y pégalo).
3. Renombra la copia exactamente como `.env`
4. Ábrelo y coloca tu **API Key de Google Gemini** en la variable `GEMINI_API_KEY`. (Si no tienes una, la puedes generar gratis en [Google AI Studio](https://aistudio.google.com/)).

### 3. Ejecutar la Aplicación

Si estás en **Windows**, simplemente dale doble clic al archivo `iniciar.bat` que se encuentra en esta carpeta principal. Este script instalará automáticamente todas las dependencias y arrancará ambos servidores (Frontend y Backend).

Si prefieres hacerlo de forma **manual** (Mac, Linux o Windows por consola):

#### A. Iniciar el Backend (FastAPI)
Abre una terminal y ejecuta:
```bash
cd backend
python -m venv venv

# En Windows:
venv\Scripts\activate
# En Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload
```
*El backend quedará corriendo en `http://localhost:8000`*

#### B. Iniciar el Frontend (React)
Abre OTRA terminal y ejecuta:
```bash
cd frontend
npm install
npm run dev
```
*El frontend quedará corriendo en `http://localhost:5173`*

---

## 🧑‍💻 Usuarios por Defecto
Una vez que el sistema arranque por primera vez, creará automáticamente un usuario administrador y un motor de reglas base.

**Panel de Administrador:**
- **Email:** `admin@ucaldas.edu.co`
- **Contraseña:** `Admin123*`

Desde allí podrás ver el ranking de aspirantes y configurar las reglas de calificación.
