
# 🩺 Health-Management-Backend

Web APIs for the Health Management Application  
Built to support pregnant women with personalized care, diet plans, exercises, and health monitoring.  
Powered by **AAT**.

---

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/health-management-backend.git
cd health-management-backend
```
---
### 2. Set Up Environment

##### . Create a folder named ```.env```

##### . Copy the contents of ```env.txt``` into a file called ```.env``` inside that folder:

```bash CopyEdit
.env/
  └── .env
```
##### Example ```.env``` values:

```makefileCopyEdit
DJANGO_ENV=development
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
...
```
---
### 3. Create a Virtual Environment & Install Dependencies

```bashCopyEdit
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```
---
### 4. Database Setup
##### . You can use **PostgreSQL** or **SQLite** locally.

Apply migrations:
```bashCopyEdit
python manage.py makemigrations
python manage.py migrate
```
---
### 5. Create a Superadmin User
```bash
python manage.py create_superadmin
```
---
### 6. Run the Development Server
```bash
python manage.py runserver
```
Open your browser and visit:
👉 ```http://localhost:8000/```

---
# 📑 Features

##### . ✅ JWT Authentication (SimpleJWT)

##### . ✅ Role-based Access: ```superadmin```, ```doctor```, ```patient```

##### . ✅ Diet Plans with Meals, Scheduling, and Completion Status

##### . ✅ Exercise Tracking and Skipping/Completion Logging

##### . ✅ Health Status Monitoring (weight, height, BMI, streaks)

##### . ✅ Patient Questionnaire System

##### . ✅ Lab Reports Uploads

##### . ✅ Audio Reason for Skipped Meals or Exercises

##### . ✅ OTP Login (MSG91 Integration)

##### . ✅ Swagger/OpenAPI Documentation
---

# 🧪 API Documentation
Once server is running:
##### . Swagger ```UI → http://localhost:8000/api/schema/swagger-ui/```
##### . ReDoc Docs → ```http://localhost:8000/api/schema/redoc/```

---

# 📦 Tech Stack
##### . Python 3.10+

##### . Django 4.x

##### . Django REST Framework

##### . PostgreSQL / SQLite

##### . SimpleJWT (token-based auth)

##### . DRF Spectacular (Swagger/OpenAPI)

##### . AWS S3 / Local Media File Support

##### . MSG91 OTP API
---

# 🗂️ Project Structure
```bash
users/            → Custom users, roles, OTP, profiles
doctor/           → Doctor-side features: diet plans, patients
patient/          → Patient-side: exercise, diet, reports, health
HealthManagment/  → Django settings and project config
```
--- 

# 🧑‍💻 Developer Notes
Useful Commands:
```
# Start dev server
python manage.py runserver

# Run DB migrations
python manage.py makemigrations
python manage.py migrate

# Create a superuser
python manage.py create_superadmin
```
---

# 🤝 Contributors

##### . Sam – Backend Lead Developer

##### . AAT Health Team – Domain Experts, QA, and Project Scope

----

# 📬 License

######  Private project – All rights reserved © AAT Health.
---

```✅ You can now use this version as your main `README.md`.  
Let me know if you want to include exercise endpoints or AWS S3 config instructions too.```
