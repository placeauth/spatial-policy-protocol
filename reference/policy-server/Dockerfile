FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY reference/policy-server ./reference/policy-server
COPY reference/admission ./reference/admission
COPY schema ./schema
COPY examples ./examples

RUN python -m pip install --no-cache-dir .

ENV SPP_SCHEMA_DIR=/app/schema
ENV SPP_POLICY=/app/examples/hospital.yaml

EXPOSE 8000

CMD ["uvicorn", "spp.server:app", "--host", "0.0.0.0", "--port", "8000"]