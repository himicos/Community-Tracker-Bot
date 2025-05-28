FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create data directory for SQLite database and account storage
RUN mkdir -p data

# Copy the rest of the application
COPY . .

# Run the bot
CMD ["python", "main.py"]
