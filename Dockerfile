# 1. Use a lightweight Python version
FROM python:3.10-slim-bullseye

# 2. Install the specific system tools needed to build dlib and OpenCV
# This is where the standard Render build was failing.
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libopenblas-dev \
    liblapack-dev \
    libx11-dev \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# 3. Set the working directory
WORKDIR /app

# 4. Copy and install requirements 
# We use --no-cache-dir to keep the image small
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of your app's code
COPY . .

# 6. Tell Render to use port 5000
EXPOSE 5000

# 7. Start command (matches your current setup)
CMD ["gunicorn", "app:app", "--workers", "1", "--timeout", "120", "--bind", "0.0.0.0:5000"]
