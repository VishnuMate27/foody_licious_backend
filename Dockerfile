# Use Python 3.11
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first (for caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Hugging Face requires port 7860
EXPOSE 7860

# Run with Gunicorn WSGI server
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:7860", "run:app"]
