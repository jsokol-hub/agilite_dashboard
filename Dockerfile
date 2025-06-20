# 1. Use an official Python runtime as a parent image
FROM python:3.9-slim

# 2. Set the working directory in the container
WORKDIR /app

# 3. Copy the requirements file into the container
COPY requirements.txt .

# 4. Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of the application's code into the container
COPY . .

# 6. Expose the port the app runs on
EXPOSE 80

# 7. Define the command to run the app using Gunicorn
# Gunicorn is a production-ready WSGI server.
# It will look for the 'server' object inside the 'app.py' file.
CMD ["gunicorn", "--bind", "0.0.0.0:80", "app:server"] 