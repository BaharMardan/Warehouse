FROM python:3.12-slim AS dependencies
WORKDIR /build
COPY backend/requirements.txt .
COPY deploy-wheels /wheels
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    && /opt/venv/bin/pip check

FROM python:3.12-slim
ARG WAREHOUSE_COMMIT
LABEL org.opencontainers.image.revision=$WAREHOUSE_COMMIT
ENV PATH="/opt/venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /code
COPY --from=dependencies /opt/venv /opt/venv
COPY backend/app ./app
COPY backend/run_migrations.py backend/backup_warehouse.py backend/extract_schema.py backend/export_live_migration.py backend/run_sql.py ./
COPY backend/migrations ./migrations
USER 65532:65532
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
