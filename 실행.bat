@echo off
chcp 65001 > nul
pip install streamlit pandas openpyxl
streamlit run daily_manager_app.py
pause
