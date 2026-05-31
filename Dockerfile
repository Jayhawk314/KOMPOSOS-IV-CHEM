FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Environment defaults
ENV KOMPOSOS_HOST=0.0.0.0
ENV KOMPOSOS_PORT=8000
ENV KOMPOSOS_RELOAD=false
ENV KOMPOSOS_LOG_LEVEL=INFO

EXPOSE 8000

# Serve the Streamlit UI (the visual app you show people). Render injects $PORT;
# fall back to 8000 locally. Shell-form CMD so ${PORT} expands.
# (The FastAPI API in api.main still exists — run it as a SEPARATE Render service
#  with start command: uvicorn api.main:app --host 0.0.0.0 --port $PORT)
CMD streamlit run streamlit_app/app.py \
    --server.port ${PORT:-8000} \
    --server.address 0.0.0.0 \
    --server.headless true \
    --server.enableCORS false \
    --server.enableXsrfProtection false
