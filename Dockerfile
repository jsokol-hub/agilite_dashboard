# Stage 1: "Builder" - for installing dependencies
# Use a specific Python version for predictability
FROM python:3.11-slim as builder

# Set the working directory
WORKDIR /app

# Copy only the requirements file to leverage Docker's layer caching
COPY requirements.txt .

# Install dependencies to the user's local directory, which is a safer practice
RUN pip install --user --no-cache-dir -r requirements.txt

# ---

# Stage 2: Final production image
# Start from the same clean Python image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy the dependencies installed in the "builder" stage
COPY --from=builder /root/.local /root/.local

# Copy all the application code
COPY . .

# Add the directory with package executables (including gunicorn) to the system PATH
# This is necessary because we used the --user flag during installation
ENV PATH=/root/.local/bin:$PATH

# Expose port 80, which Gunicorn will listen on. CapRover expects this.
EXPOSE 80

# Run the application using Gunicorn, the production standard for Python web apps
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:80", "app:server"] 