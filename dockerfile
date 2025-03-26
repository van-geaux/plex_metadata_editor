FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
COPY main.py .
COPY router.py .
COPY router_frame.js .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

# Run the NiceGUI app
CMD ["python", "main.py"]
