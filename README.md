# ZESCO Bill Anomaly Detector

Simple Flask app to upload and monitor electricity usage.


✅ 2. Create a virtual environment

python -m venv venv
This creates a folder named venv/ with your isolated environment.

If you're using Python 3 specifically, you can also use:


python3 -m venv venv
✅ 3. Activate the virtual environment
On Windows CMD:

venv\Scripts\activate
On PowerShell:

venv\Scripts\Activate.ps1
💡 If you get a permission error on PowerShell, run this once to allow scripts:

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
✅ 4. Install packages
Now that your venv is active, you can install packages like:

pip install flask
✅ 5. Deactivate when done
deactivate



run in production:

for windows:

waitress-serve --port=8080 wsgi:app

for lunux:

gunicorn -w 4 -b 0.0.0.0:8000 wsgi:app


How to use:

Push your code to GitHub.

Go to https://render.com, click "New Web Service", and connect your repo.

Set:

Build Command: pip install -r requirements.txt

Start Command: gunicorn wsgi:app

Environment: Python 3.x