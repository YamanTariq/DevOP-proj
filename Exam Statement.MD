## COMSATS UNIVERSITY ISLAMABAD

## Lahore Campus

## Department of Computer Science

# □ Lab Mid Examination ■ Terminal Examination Spring 2026

```
Course Title: DevOps for Cloud Computing Course Code: CSC 418 Credit Hours: 3(2,1)
```
Course Instructor/s: (^) Dr. M. Hasanain Ch Program^ Name^
Name:

### BS(CS)

Semester: (^6) th Batch: (^) FA2 3 Section: A-B Date: 18 May 2026
**Time Allowed: 90 Minutes Maximum Marks: 50**
Student’s Name: Reg. No.
(^)

## Q1. [CLO: 5 ; Bloom Taxonomy Level <Applying>: Develop cloud native applications

## using current DevOps tools.]

**General Instructions**

1. You will continue with the **same project** used in the mid-term evaluation.
2. The project **must** now have:
    a. A **Frontend**
    b. A **Backend/API**
    c. A **Database** (SQL or NoSQL)
3. A small or incomplete project will result in **mark deduction**.
4. All tasks must be documented clearly, with screenshots included in your final submission.
**SECTION A: CONTAINERIZATION (10 Marks)
Task A1: Docker Images**
Create separate Dockerfiles for:
- Your **frontend application**
- Your **backend application**
- Your **database
Task A2: Multi-Service Setup using Docker Compose**
Prepare a docker-compose.yml that:
- Starts all three services
- Connects them in a common network
- Persists DB data


!"#$%&'() **Submit:**

- Dockerfiles
- docker-compose.yml
- Screenshot of all containers running
**SECTION B: CI/CD AUTOMATION (1 0 Marks)**
You may use **Jenkins** , **Azure DevOps** , or **GitHub Actions**.
**Task B1: Pipeline Development**
Build a pipeline that contains at least:
1. Build stage (frontend + backend)
2. Automated tests
3. Docker image build and push to registry
4. Deployment step to Kubernetes (or staging server)
**Task B2: Trigger Configuration**
Configure the pipeline so it runs on **push/commit** or **pull request**.
!"#$%&'() **Submit:**
- Pipeline file (Jenkinsfile OR YAML workflow)
- Pipeline run screenshot (must show all stages completed)
**SECTION C: KUBERNETES ON AZURE (AKS) (1 0 Marks)**
Deploy your 3-tier application on **Azure Kubernetes Service (AKS).
Task C1: Kubernetes Manifests**
- Create an Azure Kubernetes Cluster (AKS).
- Deploy containerized application from Docker Hub onto AKS.
- Expose the app using a public IP address and provide a reachable link.
**Task C2: AKS Deployment Verification**
Your application must run correctly in the cluster.
Show:
- All pods in Running state
- Services created successfully
- Frontend connecting to backend
- Backend connecting to database


!"#$%&'() **Submit:**

- Screenshots of kubectl get pods, kubectl get svc, and the running app.
**SECTION D: SELENIUM AUTOMATED TESTING ( 5 Marks)**
Develop **Selenium test cases** for your application.
**Task E1: Test Cases (Minimum 3)**
Examples (choose any relevant to your project):
- Verify homepage loads
- Validate login or form behavior
- Check frontend-to-backend API response
- Validate navigation or button behavior
**Task E2: Execution Report**
Include the code and test execution screenshots.
!"#$%&'() **Submit:**
- Selenium scripts
- Screenshot of test run

## SECTION E: Report and Submission (15 Marks)

Submit a short report containing:

- Viva will be conduct on **19 May 2026**
- Source code files
- Screenshots of output
- Assignment report in PDF or Word format
- All file must inside in folder and make zip file
- Assignment report (zip file) name should be your **Reg. NO**


