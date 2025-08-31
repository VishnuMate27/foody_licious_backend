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

## 🔑 API Endpoints Overview

### Authentication
- **POST** `/api/auth/register`
- **POST** `/api/auth/sendVerificationCodeForRegistration`
- **POST** `/api/auth/verifyCodeAndRegisterWithPhone`
- **POST** `/api/auth/login`
- **POST** `/api/auth/sendVerificationCodeForLogin`
- **GET** `/api/auth/verifyCodeAndLoginWithPhone`