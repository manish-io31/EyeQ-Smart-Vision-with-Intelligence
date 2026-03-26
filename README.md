# 👁️‍🗨️ EYEQ - Smart Vision with Intelligence

## 📌 Project Overview

The **EYEQ - Smart Vision with Intelligence** is a full-stack intelligent surveillance application that enables real-time object detection, monitoring, and alerting using computer vision and cloud technologies. It helps in identifying potential threats and managing camera feeds through a centralized web dashboard.

---

## 🚀 Features

### 👨‍💼 Admin

- Monitor multiple camera feeds
- Configure detection thresholds
- Manage alerts and notifications
- View detection logs and analytics

### 👨‍💻 User

- Secure login/logout
- View live surveillance dashboard
- Access detection results
- Receive alert notifications

---

## 🛠 Tech Stack

- **Backend:** Python, Flask, Flask-SQLAlchemy, Flask-Login
- **Computer Vision:** AWS Rekognition, YOLO (Ultralytics), OpenCV, Pillow
- **Frontend:** HTML, CSS, JavaScript
- **Database:** SQLite / PostgreSQL
- **Cloud Services:** AWS (Rekognition, S3)
- **Communication:** Twilio (SMS), SMTP (Email)

---

## 🏗 Architecture

Camera Feed → Detection Engine (YOLO + AWS Rekognition) → Flask Backend → Database → Web Dashboard → Alerts (SMS/Email)

---

## 📊 Features Implemented

- Real-time object detection
- Threat detection with configurable thresholds
- Authentication system (Flask-Login)
- Alert system (SMS & Email integration)
- Camera integration with snapshot capture
- Database storage for detections and users
- Web-based monitoring dashboard
- Configurable detection and alert settings

---

## ⚙️ Setup Instructions

### 1️⃣ Clone Repository

```bash
git clone https://github.com/yourusername/eyeq-surveillance.git
cd eyeq-surveillance
```

2️⃣ Create Virtual Environment

```bash
python -m venv venv
venv\Scripts\activate   # Windows
```

3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

4️⃣ Configure Environment Variables

```bash
Create a .env file and add your credentials (AWS, Twilio, Email, Database).
```

5️⃣ Run the Application

```bash
   python flask_rekognition/app.py
```

6️⃣ Open in Browser

```bash
http://localhost:5000
```

## 📈 Future Enhancements

- Face recognition system
- Mobile app integration
- AI-based anomaly detection
- Role-based advanced access control

---

## 👨‍💻 Author

Manish Kumar S
