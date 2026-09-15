FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY reference/policy-server ./reference/policy-server
COPY reference/admission ./reference/admission
COPY schema ./schema
COPY demo/admission ./demo/admission
COPY sandbox/app ./sandbox/app
COPY sandbox/examples ./sandbox/examples

RUN python -m pip install --no-cache-dir .

ENV PYTHONPATH=/app/sandbox/app
EXPOSE 8080

CMD ["uvicorn", "sandbox_app:app", "--host", "0.0.0.0", "--port", "8080"]
