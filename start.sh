#!/bin/bash

# 1. Preparar el entorno Backend
cd backend

if [ ! -d "venv" ]; then
    echo "Creando entorno virtual..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt

if [ ! -f ".env" ]; then
    echo "Creando archivo .env..."
    cp .env.example .env
fi

python3 -m db.seed

# 2. Iniciar Backend en segundo plano
echo "Iniciando Backend en puerto 8000..."
python3 -m uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!

# 3. Iniciar Frontend desde la raíz
cd ..
echo "Iniciando Frontend en puerto 5500..."
echo "Accede a: http://localhost:5500/frontend/pages/mapa.html"
python3 -m http.server 5500

# Al cerrar el servidor frontend (Ctrl+C), mata también el backend
kill $BACKEND_PID