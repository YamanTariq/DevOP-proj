# Use Python
FROM python:3.11-slim

# Set where the code lives in the container
WORKDIR /app

# Copy all your files from your computer to the container
COPY . .

# Install the libraries listed in requirements.txt
RUN pip install -r requirements.txt

# Tell Docker which port the app uses
EXPOSE 5000

# Run the app exactly like you do on your terminal
CMD ["python", "app.py"]