# 1. Use an image that ALREADY has dlib and face_recognition built in
FROM animcogn/face_recognition:cpu-latest

# 2. Set the working directory
WORKDIR /app

# 3. Copy your requirements file
COPY requirements.txt .

# 4. Remove the heavy packages so Render doesn't try to build them
RUN sed -i '/face-recognition/d' requirements.txt && \
    sed -i '/dlib/d' requirements.txt && \
    sed -i '/numpy/d' requirements.txt && \
    pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of your app's code
COPY . .

# 6. Expose the port
EXPOSE 5000

# 7. Start the app
CMD ["gunicorn", "app:app", "--workers", "1", "--timeout", "120", "--bind", "0.0.0.0:5000"]