FROM python:3.12-alpine
WORKDIR /app
COPY server.py ./
COPY web ./web
EXPOSE 5186
CMD ["python", "server.py"]
