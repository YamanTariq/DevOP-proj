📌 Project Executive Summary
The Goal: Transform your existing monolithic Flask application (ChirpTown) into a fully containerized, CI/CD-automated, 3-tier microservices architecture deployed to Azure Kubernetes Service (AKS), fulfilling all requirements of the CSC418 DevOps Final Lab Exam.

🤝 Locked-In Decisions (What we are building)
To ensure we maximize marks and avoid feature creep or deployment nightmares, we have finalized the following boundaries:

Architecture: Strict 3-Tier.

Tier 1 (Frontend): Pure HTML, CSS, and Vanilla JS served by an Nginx web server. No Jinja templates.

Tier 2 (Backend): Python Flask acting purely as a RESTful JSON API.

Tier 3 (Database): Local MongoDB instance (moving away from Atlas cloud).

Containerization: docker-compose.yml linking three distinct Docker images via a shared bridge network, with a named Docker volume for MongoDB data persistence.

New Features:

Like Button: Simple integer increment in the DB.

Profile Page: View other users, their bios, and their tweets.

Edit Bio: Text-based only. NO image/profile picture uploads (avoids persistent storage nightmares on Kubernetes).

CI/CD Pipeline: GitHub Actions. It will trigger on push, run tests, build/push Docker images to DockerHub, and deploy to AKS.

Testing: Selenium with Python, running 3 distinct UI/Integration tests.

🗺️ Master Execution Plan
Phase 1: Application Refactoring (Monolith to 3-Tier API)
Objective: Sever the frontend from the backend so they can exist in separate containers.

Step 1.1: Backend API Conversion

Update app.py to remove all render_template calls.

Convert routes (/, /login, /signup, /post) into API endpoints (/api/tweets, /api/auth/login, etc.) that return standard JSON responses ({"status": "success", "data": ...}).

Switch from Flask session cookies to a simple token-based approach (or configure Flask CORS to allow cookie sharing between the Nginx container and the Flask container).

Step 1.2: Database Migration Prep

Update the MongoDB URI in app.py to read strictly from an environment variable (e.g., MONGO_URI=mongodb://db:27017/microblog), pointing to the internal Docker network rather than Atlas.

Step 1.3: Frontend Decoupling

Create a new folder named frontend/.

Move index.html, login.html, and signup.html into this folder.

Write a app.js file using fetch() to handle form submissions, login logic, and dynamically loading tweets into the DOM.

Step 1.4: Implement New Features

Backend: Add /api/users/<username> (GET bio and tweets), /api/users/bio (PUT to update bio), and /api/tweets/<id>/like (POST to increment likes).

Frontend: Create profile.html and add "Like" buttons to the tweet UI in index.html.

Phase 2: Containerization (Docker & Compose)
Objective: Fulfill Section A of the exam rubric by isolating the 3 tiers.

Step 2.1: Frontend Dockerfile

Create frontend/Dockerfile.

Base image: nginx:alpine.

Action: Copy the HTML/CSS/JS files to /usr/share/nginx/html. Add a custom nginx.conf to proxy API requests to the backend container.

Step 2.2: Backend Dockerfile

Create backend/Dockerfile (updating your existing one).

Base image: python:3.11-slim.

Action: Install requirements.txt, expose port 5000, run app.py.

Step 2.3: Database Dockerfile

Create database/Dockerfile. (Note: While we could just use the base image in compose, the rubric explicitly asks for a Dockerfile for the DB).

Base image: mongo:latest.

Step 2.4: Docker Compose Setup

Create docker-compose.yml in the root directory.

Define services: frontend (port 80:80), backend (port 5000:5000), database (port 27017:27017).

Define a custom bridge network (chirptown-network).

Define a volume (mongo-data:/data/db) attached to the database service for persistence.

Phase 3: Automated Testing (Selenium)
Objective: Fulfill Section D by ensuring the refactored UI works.

Step 3.1: Test Environment Setup

Create a tests/ directory.

Install selenium and webdriver-manager in Python.

Step 3.2: Write 3 Specific Test Cases

Test 1: Verify Homepage loads and displays the "ChirpTown" header.

Test 2: Validate Signup/Login flow (inputs credentials, clicks submit, verifies successful login state).

Test 3: Post a Tweet (inputs text, clicks submit, verifies tweet appears at the top of the feed).

Step 3.3: Execution & Documentation

Run tests locally against the Docker Compose setup.

Capture screenshots of the automated browser executing the tests.

Phase 4: CI/CD Pipeline Configuration
Objective: Fulfill Section B using GitHub Actions.

Step 4.1: GitHub Repository Setup

Push the project to a GitHub repo.

Add DockerHub and Azure credentials as GitHub Repository Secrets.

Step 4.2: Pipeline YAML Creation

Create .github/workflows/ci-cd.yml.

Stage 1 (Build & Test): Checkout code, setup Python, run a quick sanity check/unit test.

Stage 2 (Docker Build & Push): Log in to DockerHub, build the Frontend and Backend images, push them to yourusername/chirptown-frontend:latest and yourusername/chirptown-backend:latest.

Stage 3 (Deploy to AKS): Authenticate with Azure, use kubectl apply commands to deploy to the cluster.

Phase 5: Kubernetes on Azure (AKS)
Objective: Fulfill Section C by taking the app to the cloud.

Step 5.1: AKS Cluster Creation

Log into Azure Portal and provision a basic, low-cost AKS cluster.

Step 5.2: Write Kubernetes Manifests (k8s/ folder)

mongo.yaml: Deployment and PersistentVolumeClaim for the DB.

backend.yaml: Deployment (pulling your image from DockerHub) and ClusterIP Service.

frontend.yaml: Deployment (pulling your image) and a LoadBalancer Service to expose the app to the internet with a Public IP.

Step 5.3: Deployment Verification

Run kubectl get pods, kubectl get svc.

Verify the frontend connects to the backend, and backend to the DB in the cloud. Take screenshots.

Phase 6: Final Documentation and Submission
Objective: Fulfill Section E and prepare for the Viva on May 19.

Step 6.1: Organize Files

Ensure all source code is neatly organized in folders (frontend, backend, database, tests, k8s).

Step 6.2: Report Generation

Compile the PDF/Word document containing all required screenshots (Docker Compose running, Pipeline success, K8s Pods/Services, app UI via Public IP, Selenium execution).

Step 6.3: Zip & Submit

Package everything into a single Zip file named [Your Reg. No].zip.