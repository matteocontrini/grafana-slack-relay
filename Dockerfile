FROM python:3.11-alpine

WORKDIR /app

COPY . .
RUN pip install pipenv
RUN pipenv install --dev --system

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

CMD ["python", "app.py"]
