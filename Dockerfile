FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY templates/ templates/
RUN mkdir -p /data/uploads
VOLUME ["/data"]
EXPOSE 8088
CMD ["gunicorn", "-b", "0.0.0.0:8088", "-w", "2", "--timeout", "120", "app:app"]
