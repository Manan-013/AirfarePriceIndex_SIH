@echo off
title Live Flight Price Fetcher - SIH 26056
echo ========================================================
echo   Starting Live Flight Price Fetcher (MoSPI SIH 26056)
echo   Opening in your browser at http://localhost:8000
echo ========================================================
start http://localhost:8000
python server.py
pause
