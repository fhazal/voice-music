FROM python:3.12-slim
RUN pip install --no-cache-dir faster-whisper==1.2.1 "av<17" fastapi uvicorn nvidia-cublas-cu12 nvidia-cudnn-cu12
ENV LD_LIBRARY_PATH=/usr/local/lib/python3.12/site-packages/nvidia/cublas/lib:/usr/local/lib/python3.12/site-packages/nvidia/cudnn/lib
WORKDIR /app
COPY app.py .
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8770"]
