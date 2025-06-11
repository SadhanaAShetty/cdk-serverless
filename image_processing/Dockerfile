FROM python:3.10-slim


COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY image_resize.py /app/


WORKDIR /app


CMD ["python", "image_resize.py"]
