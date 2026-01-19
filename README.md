---
title: Flask Authentication API
emoji: 🔑
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
license: mit
---

# Flask Authentication API 🚀

This is a Flask-based authentication backend hosted on **Hugging Face Spaces** using the Docker SDK.  
It provides endpoints for user registration, login, and phone verification.  

---

## 🌍 Base URL
Once deployed, your API will be available at:

https://vishnumate09-foody_licious_backend.hf.space


##  Running Locally (Without Docker)

### 1️. Create Virtual Environment

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 2️. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3️. Run Flask App

```bash
python run.py
```

App will be available at:

```
http://localhost:7860
```

---

##  Running with Docker (Recommended)

### 1️. Build Image

```bash
docker-compose build
```

### 2️. Start Container

```bash
docker-compose up -d
```

### 3️. View Logs

```bash
docker-compose logs -f api
```

### 4️. Stop Services

```bash
docker-compose down
```

---

##  Production Server (Gunicorn)

Gunicorn is used inside Docker:

```bash
gunicorn -w 4 -b 0.0.0.0:7860 run:app
```

* 4 workers (configurable)
* Sync workers (Flask-compatible)

---


## 🔑 API Endpoints Overview

### Authentication
- **POST** `/api/auth/register`
- **POST** `/api/auth/sendVerificationCodeForRegistration`
- **POST** `/api/auth/verifyCodeAndRegisterWithPhone`
- **POST** `/api/auth/login`
- **POST** `/api/auth/sendVerificationCodeForLogin`
- **GET** `/api/auth/verifyCodeAndLoginWithPhone`