FROM python:3.13-slim
WORKDIR /app

# Node.js — needed so npx can launch the Arize Phoenix MCP server (stdio) in-container
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

RUN npm install -g @arizeai/phoenix-mcp

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN adduser --disabled-password --gecos "" myuser && chown -R myuser:myuser /app
COPY . .
USER myuser

ENV PATH="/home/myuser/.local/bin:$PATH"
ENV npm_config_cache=/tmp/.npm

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port $PORT"]
