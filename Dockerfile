FROM python:3.11-slim

WORKDIR /app
COPY app.py .

EXPOSE 9000

CMD ["python", "app.py"]
