# 1. Start with an official Python base image.
# Using python:3.9-slim is a good choice for a balance of features and size.
FROM python:3.9-slim

# --- ADD THIS BLOCK TO INSTALL NETCAT ---
# Install system dependencies needed for the entrypoint script.
# - apt-get update: Refreshes the list of available packages.
# - apt-get install -y ...: Installs the package without asking for confirmation.
# - rm -rf ...: Cleans up the cache to keep the final image size small.
RUN apt-get update && apt-get install -y netcat-traditional && rm -rf /var/lib/apt/lists/*

# 2. Set the working directory inside the container.
# All subsequent commands will run from here.
WORKDIR /app

# 3. Copy only the requirements file first.
# This leverages Docker's layer caching. If requirements.txt doesn't change,
# Docker won't re-install all the packages on every build.
COPY requirements.txt .

# 4. Install the Python dependencies.
# --no-cache-dir keeps the image size smaller.
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of your application code into the container.
COPY . .

# Make the entrypoint script executable inside the container
RUN chmod +x /app/entrypoint.sh

# 6. Expose the port that Uvicorn will run on (default 8000)
EXPOSE 8000

# 7. Use the entrypoint script as the default command, which runs migrations
#    and then launches the server; we rely on entrypoint.sh to read PORT
CMD ["/bin/sh", "-c", "./entrypoint.sh"]