# Usa una imagen base de Python
FROM python:3.11-slim

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# --- INSTALACIÓN DE TESSERACT OCR Y LIBMAGIC ---
# Actualiza la lista de paquetes e instala Tesseract, libmagic y otras dependencias
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    libleptonica-dev \
    libmagic1 \
    pkg-config \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Copia el archivo de requerimientos de Python
COPY requirements.txt .

# Instala las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto del código de tu aplicación al contenedor
COPY . .

# Expone el puerto que usará tu aplicación
EXPOSE 10000

# Comando para ejecutar la aplicación
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]
