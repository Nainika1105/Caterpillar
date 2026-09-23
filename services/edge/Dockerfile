FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for voice system
RUN apt-get update && apt-get install -y \
    espeak \
    espeak-ng \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy edge service code
COPY . .

# Default to mock voice (no audio hardware in container)
ENV VOICE_BACKEND=mock
ENV MQTT_HOST=mosquitto
ENV MQTT_PORT=1883
ENV MACHINE_ID=BH001
ENV SITE_ID=S01
ENV OPERATOR_ID=OP1011
ENV LOG_LEVEL=INFO

CMD ["python", "gateway.py"]
