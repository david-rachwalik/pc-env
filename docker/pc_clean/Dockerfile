# Use the latest Python image
FROM python:3.12-alpine

# Set the working directory in the container
WORKDIR /app

# Copy specific Python files (custom modules) to the container
COPY python/modules/boilerplates/logging_boilerplate.py /root/.local/lib/python3.12/site-packages/
COPY python/modules/boilerplates/shell_boilerplate.py /root/.local/lib/python3.12/site-packages/
COPY python/modules/app_backup_data.py /root/.local/lib/python3.12/site-packages/
COPY python/modules/game_backup_data.py /root/.local/lib/python3.12/site-packages/
# Copy and rename Python files (command scripts) to omit .py extension
COPY python/commands/pc_clean.py /root/.local/bin/pc_clean

# Set execute permissions for command scripts
# RUN chmod +x /root/.local/bin/*

# Install required packages
# RUN pip install -r requirements.txt  # Uncomment if you have a requirements.txt file
RUN pip install colorlog pytz dirsync

# Update PATH to include /root/.local/bin
# ENV PATH="/root/.local/bin:${PATH}"

# Set the default command to run your Python script with arguments
CMD ["python", "/root/.local/bin/pc_clean", "--debug"]


# --- Usage Example (run from project root, build image, and run container) ---
# cd C:\Users\david\Repos\pc-env
# docker build -t python-runner -f docker/pc_clean/Dockerfile .
# docker run --rm -v ${PWD}:/app -v C:/:/mnt/c -v D:/:/mnt/d python-runner

# --- Test Run (specify command) ---
# docker run --rm --name python-runner-container python-runner <command>
# --- Test Run (interactive run) ---
# docker run --rm -it --name python-runner-container python-runner /bin/sh
