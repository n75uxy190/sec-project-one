FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir flask
COPY server.py .
EXPOSE 12434
CMD ["python", "server.py"]
