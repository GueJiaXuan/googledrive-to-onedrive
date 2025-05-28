@echo off
echo Installing required Python packages...

REM Core packages
pip install pandas geopandas fiona

REM Google API client libraries
pip install google-api-python-client google-auth google-auth-oauthlib openpyxl

echo All packages installed.
pause
