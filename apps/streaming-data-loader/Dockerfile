FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy only requirements first to leverage Docker cache
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . ./

# Set environment variables for defaults (optional ones)
ENV HYDRO_SERVICE_URL=https://playground.hydroserver.org
ENV LOG_FILE=/app/logs/hydroloader.log

# Expose the logs directory (useful for debugging in container setups)
VOLUME ["/app/logs"]

# Ensure the logs directory exists
RUN mkdir -p /app/logs

# Define the default command to run the application
CMD [ \
    "python", "main.py" \
]
