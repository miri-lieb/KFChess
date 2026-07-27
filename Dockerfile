FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip

COPY pyproject.toml ./
COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN pip install --no-cache-dir -e .

EXPOSE 8765

ENV NETWORK_HOST=0.0.0.0
ENV NETWORK_PORT=8765

CMD ["python", "-m", "network.server_main"]
