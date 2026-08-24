@echo off
cd /d "C:\Auto_blogpost\.claude\worktrees\competent-tereshkova-715eb3\blog_bot"
start "" /B "C:\Users\sjtpa\AppData\Local\Python\pythoncore-3.14-64\python.exe" -m streamlit run app.py --server.headless true
timeout /t 5 /nobreak >nul
start http://localhost:8501
