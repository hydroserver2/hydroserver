FROM python:3.11-slim

ARG RELEASE
ENV RELEASE=${RELEASE}

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ENV DATA_MGMT_REPO=hydroserver2/hydroserver-data-management-app
ENV DATA_MGMT_ASSET=data-management-app-${RELEASE}.zip

WORKDIR /app

RUN test -n "$RELEASE" || (echo "RELEASE is required but not set." && exit 1)

RUN apt-get update && apt-get install -y unzip curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

RUN curl -L -o data_mgmt_app.zip https://github.com/${DATA_MGMT_REPO}/releases/download/${RELEASE}/${DATA_MGMT_ASSET} && \
    unzip data_mgmt_app.zip -d data_mgmt_app && \
    mkdir -p interfaces/web/static/web && \
    cp -f data_mgmt_app/dist/index.html templates/index.html && \
    cp -r data_mgmt_app/dist/* interfaces/web/static/web/ && \
    sed -i "s@<script id=\"app-settings\" type=\"application/json\"></script>@{{ settings|json_script:\\\"app-settings\\\" }}@" templates/index.html && \
    rm -rf data_mgmt_app data_mgmt_app.zip
