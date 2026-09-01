ARG BUILDPLATFORM
FROM --platform=$BUILDPLATFORM node:22-slim AS frontend-builder

WORKDIR /build

COPY packages/hydroserver-ts packages/hydroserver-ts
WORKDIR /build/packages/hydroserver-ts
RUN npm ci && npm run build

WORKDIR /build
COPY packages/qc-utils packages/qc-utils
WORKDIR /build/packages/qc-utils
RUN npm ci --workspaces=false && npm run build

WORKDIR /build
COPY packages/design-system packages/design-system
COPY apps/data-management apps/data-management
WORKDIR /build/apps/data-management
RUN npm ci && npm run django-build

WORKDIR /build
COPY apps/qc-app apps/qc-app
WORKDIR /build/apps/qc-app
RUN npm ci --workspaces=false && \
    npm install ../../packages/qc-utils --no-save --package-lock=false --workspaces=false && \
    printf 'VITE_APP_ROUTE=/qc/\n' > .env && \
    npm run django-build

FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app/django

COPY django/requirements.txt .
COPY packages/hydroserverpy /app/packages/hydroserverpy
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install ../packages/hydroserverpy

COPY . /app

COPY --from=frontend-builder /build/apps/data-management/dist/index.html templates/index.html
COPY --from=frontend-builder /build/apps/data-management/dist interfaces/web/static/web
RUN sed -i \
    -e "s@<script id=\"app-settings\" type=\"application/json\"></script>@{{ settings|json_script:\"app-settings\" }}@" \
    -e "s@<script id=\"current-user\" type=\"application/json\"></script>@{{ current_user|json_script:\"current-user\" }}@" \
    templates/index.html

COPY --from=frontend-builder /build/apps/qc-app/dist/index.html templates/qc/index.html
COPY --from=frontend-builder /build/apps/qc-app/dist interfaces/web/static/qc
RUN sed -i \
    -e "s@<script id=\"app-settings\" type=\"application/json\"></script>@{{ settings|json_script:\"app-settings\" }}@" \
    -e "s@<script id=\"current-user\" type=\"application/json\"></script>@{{ current_user|json_script:\"current-user\" }}@" \
    templates/qc/index.html

RUN python manage.py collectstatic --noinput

ENV STRICT_SECURITY=True
ENV SAME_ORIGIN_FRONTEND=True
