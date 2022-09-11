FROM tiangolo/uvicorn-gunicorn-fastapi:python3.9

WORKDIR /

# Copy requirements.txt
COPY requirements.txt /requirements.txt

# Install requirements
RUN pip install --no-cache-dir -r requirements.txt

# Copy project into container
COPY main.py /main.py
COPY worldcat_api.py /worldcat_api.py

