FROM python:3.11-slim

ARG RELEASE
ENV RELEASE=${RELEASE}

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app/django

RUN test -n "$RELEASE" || (echo "RELEASE is required but not set." && exit 1)

RUN apt-get update && apt-get install -y unzip git && rm -rf /var/lib/apt/lists/*

COPY django/requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install git+https://github.com/hydroserver2/hydroserver.git@${RELEASE}#subdirectory=packages/hydroserverpy

COPY . /app

RUN unzip /app/data_mgmt_app.zip -d /tmp/data_mgmt_app && \
    mkdir -p interfaces/web/static/web && \
    cp -f /tmp/data_mgmt_app/dist/index.html templates/index.html && \
    cp -r /tmp/data_mgmt_app/dist/* interfaces/web/static/web/ && \
    sed -i "s@<script id=\"app-settings\" type=\"application/json\"></script>@{{ settings|json_script:\"app-settings\" }}@" templates/index.html && \
    rm -rf /tmp/data_mgmt_app /app/data_mgmt_app.zip

RUN unzip /app/qc_app.zip -d /tmp/qc_app && \
    mkdir -p interfaces/web/static/qc && \
    cp -f /tmp/qc_app/dist/index.html templates/qc/index.html && \
    cp -r /tmp/qc_app/dist/* interfaces/web/static/qc/ && \
    sed -i "s@<script id=\"app-settings\" type=\"application/json\"></script>@{{ settings|json_script:\"app-settings\" }}@" templates/qc/index.html && \
    rm -rf /tmp/qc_app /app/qc_app.zip
