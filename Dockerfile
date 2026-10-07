# TradeALGO 24/7 Quantitative Execution Engine & Web Terminal
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Kolkata

WORKDIR /app

# Install system packages (tzdata for accurate IST Indian market time)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    curl \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy codebase
COPY . .

# Ensure storage directories exist
RUN mkdir -p audit_logs data

# Streamlit port
EXPOSE 8501

# Default execution: 24/7 autonomous paper trading daemon
CMD ["python", "run_90day_logger.py", "--daemon"]
