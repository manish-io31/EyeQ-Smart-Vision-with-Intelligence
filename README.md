# EYEQ - Flask Surveillance System

A comprehensive surveillance system built with Flask, AWS Rekognition, and computer vision technologies for real-time object detection and alerting.

## Features

- **Real-time Object Detection**: Uses AWS Rekognition and YOLO (Ultralytics) for detecting objects, people, and potential threats
- **Web-based Dashboard**: Monitor camera feeds and detection results through a responsive web interface
- **Authentication System**: Secure login/logout with Flask-Login
- **Alert Management**: Configurable alerts for high-threat objects with SMS and email notifications
- **Camera Integration**: Support for multiple camera feeds with snapshot capture
- **Database Storage**: SQLite/PostgreSQL support for storing detection data and user information
- **Configurable Thresholds**: Adjustable confidence thresholds for detection and alerting

## Technologies Used

- **Backend**: Flask, Flask-SQLAlchemy, Flask-Login
- **Computer Vision**: AWS Rekognition, Ultralytics YOLO, OpenCV, Pillow
- **Cloud Services**: AWS (Rekognition, S3 for storage)
- **Communication**: Twilio (SMS), SMTP (Email)
- **Frontend**: HTML, CSS, JavaScript
- **Database**: SQLite (default) or PostgreSQL

## Installation

### Prerequisites

- Python 3.8+
- AWS Account with Rekognition access
- Twilio Account (for SMS alerts)
- SMTP Email Account (for email alerts)

### Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/eyeq-surveillance.git
   cd eyeq-surveillance
   ```

2. Create a virtual environment:

   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the root directory with your configuration:

   ```env
   SECRET_KEY=your-secret-key-here
   DEBUG=true

   # Database
   DATABASE_URL=sqlite:///./surveillance.db

   # AWS Configuration
   AWS_ACCESS_KEY_ID=your-aws-access-key
   AWS_SECRET_ACCESS_KEY=your-aws-secret-key
   AWS_REGION=us-east-1

   # Detection Settings
   DETECTION_CONFIDENCE_THRESHOLD=35.0
   ALERT_CONFIDENCE_THRESHOLD=65.0
   ALERT_COOLDOWN_SECONDS=30

   # Twilio SMS
   TWILIO_ACCOUNT_SID=your-twilio-sid
   TWILIO_AUTH_TOKEN=your-twilio-token
   TWILIO_FROM_NUMBER=+1234567890
   ADMIN_PHONE_NUMBER=+0987654321

   # Email Configuration
   EMAIL_ADDRESS=your-email@gmail.com
   EMAIL_PASSWORD=your-email-password
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   ```

## Configuration

The system supports various configuration options through environment variables:

- **Detection Thresholds**: Adjust `DETECTION_CONFIDENCE_THRESHOLD` and `ALERT_CONFIDENCE_THRESHOLD` to fine-tune detection sensitivity
- **Alert Labels**: Modify `HIGH_THREAT_LABELS` in `config.py` to customize which detected objects trigger alerts
- **Database**: Change `DATABASE_URL` to use PostgreSQL or other SQLAlchemy-supported databases
- **Session Settings**: Configure session lifetime and cookie settings

## Usage

1. Run the application:

   ```bash
   python flask_rekognition/app.py
   ```

2. Open your browser and navigate to `http://localhost:5000`

3. Log in with default credentials (or create a new user)

4. Access the dashboard to view camera feeds and detection results

5. Configure cameras and alert settings through the web interface

## Project Structure

```
eyeq-surveillance/
├── flask_rekognition/
│   ├── app.py              # Main Flask application
│   ├── config.py           # Configuration settings
│   ├── models.py           # Database models
│   ├── routes/             # Flask blueprints
│   │   ├── auth.py         # Authentication routes
│   │   ├── dashboard.py    # Dashboard routes
│   │   ├── camera.py       # Camera management routes
│   │   └── alerts.py       # Alert management routes
│   ├── services/           # Business logic services
│   │   ├── rekognition_service.py
│   │   └── alert_service.py
│   ├── templates/          # HTML templates
│   ├── static/             # CSS, JS, images
│   └── snapshots/          # Captured images
├── config/                 # Additional configuration
├── detection/              # Detection models and scripts
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## API Endpoints

- `GET /` - Redirect to dashboard
- `GET /login` - User login
- `GET /dashboard` - Main dashboard
- `GET /camera` - Camera management
- `GET /alerts` - View alerts
- `POST /api/detect` - Trigger object detection

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- AWS Rekognition for object detection capabilities
- Ultralytics for YOLO implementation
- Flask community for the excellent web framework
- OpenCV for computer vision utilities
