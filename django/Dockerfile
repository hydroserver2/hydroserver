FROM python:3.11-slim

ARG RELEASE
ENV RELEASE=${RELEASE}

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN test -n "$RELEASE" || (echo "RELEASE is required but not set." && exit 1)

RUN apt-get update && apt-get install -y unzip git && rm -rf /var/lib/apt/lists/*

COPY django/requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install git+https://github.com/hydroserver2/hydroserver.git@${RELEASE}#subdirectory=packages/hydroserverpy

COPY . .

RUN unzip data_mgmt_app.zip -d data_mgmt_app && \
    mkdir -p django/interfaces/web/static/web && \
    cp -f data_mgmt_app/dist/index.html django/templates/index.html && \
    cp -r data_mgmt_app/dist/* django/interfaces/web/static/web/ && \
    sed -i "s@<script id=\"app-settings\" type=\"application/json\"></script>@{{ settings|json_script:\"app-settings\" }}@" django/templates/index.html && \
    rm -rf data_mgmt_app data_mgmt_app.zip
