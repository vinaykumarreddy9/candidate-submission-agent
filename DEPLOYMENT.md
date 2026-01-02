# 🚀 Streamlit Cloud Deployment Guide

## ⚠️ Important: Architecture Consideration

This application has **two components**:
1. **Frontend** (Streamlit) - Can be deployed to Streamlit Cloud
2. **Backend** (FastAPI) - Requires separate hosting

### Deployment Options

#### Option 1: Streamlit Cloud + External Backend (Recommended)

**Frontend**: Deploy to Streamlit Cloud (Free)  
**Backend**: Deploy to one of these platforms:
- [Render](https://render.com/) (Free tier available)
- [Railway](https://railway.app/) (Free tier available)
- [Fly.io](https://fly.io/) (Free tier available)
- [Heroku](https://www.heroku.com/)

#### Option 2: All-in-One Deployment

Deploy both frontend and backend to a single platform:
- [Hugging Face Spaces](https://huggingface.co/spaces) (Supports Docker)
- [Google Cloud Run](https://cloud.google.com/run)
- [AWS ECS](https://aws.amazon.com/ecs/)

---

## 📋 Streamlit Cloud Deployment Steps

### 1. Prerequisites
- GitHub account with this repository
- Streamlit Cloud account (free at [share.streamlit.io](https://share.streamlit.io))

### 2. Deploy Frontend to Streamlit Cloud

1. **Go to Streamlit Cloud**
   - Visit https://share.streamlit.io
   - Sign in with GitHub

2. **Create New App**
   - Click "New app"
   - Repository: `vinaykumarreddy9/candidate-submission-agent`
   - Branch: `main`
   - Main file path: `frontend/app.py`

3. **Configure Secrets**
   Click "Advanced settings" and add these secrets:
   ```toml
   GROQ_API_KEY = "your_groq_api_key"
   BACKEND_URL = "your_backend_url_here"
   ```

4. **Deploy**
   - Click "Deploy!"
   - Wait 2-3 minutes for build

### 3. Deploy Backend (Example: Render)

1. **Create Render Account**
   - Visit https://render.com
   - Sign up with GitHub

2. **Create Web Service**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Name: `digot-ai-backend`
   - Environment: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`

3. **Add Environment Variables**
   ```
   GROQ_API_KEY=your_groq_api_key
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your_email@gmail.com
   SMTP_PASSWORD=your_app_password
   SENDER_EMAIL=your_email@gmail.com
   ```

4. **Deploy**
   - Click "Create Web Service"
   - Copy the deployed URL (e.g., `https://digot-ai-backend.onrender.com`)

5. **Update Streamlit Secrets**
   - Go back to Streamlit Cloud
   - Update `BACKEND_URL` with your Render URL

---

## 🔧 Alternative: Local Backend + Cloud Frontend

If you want to keep the backend running locally:

1. **Deploy only frontend to Streamlit Cloud**
2. **Expose local backend using ngrok**:
   ```bash
   # Install ngrok
   choco install ngrok  # Windows
   
   # Start your backend
   uvicorn backend.main:app --reload
   
   # In another terminal, expose it
   ngrok http 8000
   ```
3. **Update Streamlit secrets** with the ngrok URL

---

## 📝 Deployment Checklist

- [ ] `.streamlit/config.toml` created
- [ ] `.python-version` file created
- [ ] `requirements.txt` is up to date
- [ ] GitHub repository is public
- [ ] Backend deployed and URL obtained
- [ ] Streamlit Cloud secrets configured
- [ ] API keys are valid
- [ ] SMTP credentials are correct
- [ ] Test the deployed app

---

## 🐛 Troubleshooting

### "Module not found" errors
- Ensure all dependencies are in `requirements.txt`
- Check Python version compatibility

### "Connection refused" errors
- Verify `BACKEND_URL` in Streamlit secrets
- Ensure backend is running and accessible
- Check CORS settings in FastAPI

### "API Key invalid" errors
- Verify `GROQ_API_KEY` in secrets
- Ensure no extra spaces in the key

---

## 📞 Support

If you encounter issues:
1. Check Streamlit Cloud logs
2. Check backend logs (Render/Railway dashboard)
3. Open an issue on GitHub

---

**Note**: For production use, consider using a managed database and implementing proper authentication.
