@echo off
title FoodRescue AI Server
echo ========================================================
echo   Starting FoodRescue AI Development Server...
echo ========================================================
echo.
echo URL: http://127.0.0.1:5000
echo.
echo Demo Accounts:
echo   - Restaurant: chef@greengarden.com / Chef@123
echo   - NGO:        contact@cityrelief.org / Ngo@123
echo   - Volunteer:  alex@volunteer.com / Volunteer@123
echo   - Admin:      admin@foodrescue.ai / Admin@123
echo.
echo Press Ctrl+C to stop the server at any time.
echo ========================================================
python app.py
pause
