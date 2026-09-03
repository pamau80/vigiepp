# VigiEPP — imagen cloud (CPU) — build v32
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    ULTRALYTICS_OFFLINE=false

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# PyTorch CPU primero (más liviano que CUDA)
RUN pip install --upgrade pip \
 && pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install -r /app/backend/requirements.txt

COPY backend /app/backend
COPY frontend /app/frontend
COPY forense/requirements.txt /app/forense/requirements.txt
RUN pip install -r /app/forense/requirements.txt
COPY forense /app/forense

# Modelos: copiar si existen en build context; si no, se descargan al arrancar
# Datos mutables van a VIGIEPP_DATA_DIR (/data) cuando hay volumen Railway
RUN mkdir -p /app/backend/models /app/backend/data/models /app/backend/data/faces /data /data/forense

# Descargar pesos EPP + rostros en build (mejor arranque en cloud)
RUN curl -fsSL -o /app/backend/models/best_ppe.pt \
      "https://huggingface.co/ayushgupta7777/safetyvision-yolov8/resolve/main/v2/best.pt" \
 && curl -fsSL -o /app/backend/data/models/face_detection_yunet_2023mar.onnx \
      "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx" \
 && curl -fsSL -o /app/backend/data/models/face_recognition_sface_2021dec.onnx \
      "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx"

WORKDIR /app/backend
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
