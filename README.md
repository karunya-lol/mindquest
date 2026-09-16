# MindQuest 🧠

**Student Support & Wellbeing Check-In Platform**

MindQuest is a local-first student support platform that combines **Machine Learning, NLP, Flask, SQLite, and n8n automation** to help students share concerns and connect with human support.

## 🌐 Localhost Links

- **Student Home:** http://127.0.0.1:5000/
- **Support Chat:** http://127.0.0.1:5000/support-status
- **Staff Dashboard:** http://127.0.0.1:5000/staff
- **Insights:** http://127.0.0.1:5000/insights
- **n8n Dashboard:** http://localhost:5678

> These links work when the Flask and n8n servers are running on the same computer.

## ✨ Features

- Anonymous student check-ins
- TF-IDF + Logistic Regression classification
- Broad support categories and recommendations
- Human support request system
- Urgent human-support workflow
- n8n automation with email notification
- Student ↔ Support Team messaging
- Staff dashboard
- Support insights
- SQLite database
- No paid APIs required

## 🏗️ Architecture

Student → Flask → Safety Check → ML Classification → Support Suggestions → SQLite

Urgent Request → Human Support → n8n → Email Notification

## 🛠️ Tech Stack

**Python • Flask • scikit-learn • TF-IDF • Logistic Regression • SQLite • HTML • CSS • JavaScript • n8n • Git/GitHub**

## 🤖 ML Categories

- Academic Pressure
- General Stress
- Social Concerns
- Homesickness
- Need to Talk
- General Support

The model uses a **synthetic dataset** and is designed for broad support categorization, not medical diagnosis.

## 📁 Project Structure

mindquest/
├── app.py
├── model.py
├── mindquest_model.pkl
├── mindquest.db
├── data/
│   └── training_data.csv
└── templates/
    ├── index.html
    ├── result.html
    ├── urgent.html
    ├── support_requested.html
    ├── support_status.html
    ├── insights.html
    └── staff.html

## 🚀 Run Locally

    cd mindquest
    source venv/bin/activate
    python3 model.py
    python3 app.py

Then open:

http://127.0.0.1:5000/

## ⚡ n8n Automation

Start n8n:

    n8n

Open:

http://localhost:5678

Production webhook:

    http://localhost:5678/webhook/mindquest-support

Urgent requests trigger the n8n workflow and notify the support team by email. Normal check-ins do not send emails.

## 🔐 Privacy & Safety

- Uses synthetic training data
- Does not diagnose users
- Urgent requests bypass ML and are routed toward human support
- Designed to run locally
- No paid cloud APIs required

## 🎯 Skills Demonstrated

**Machine Learning • NLP • Python • Flask • SQL • SQLite • n8n • REST APIs • Full-Stack Development • Git/GitHub • AI Automation**

## 📌 Project Status

**Working local prototype built for educational and demonstration purposes.**
