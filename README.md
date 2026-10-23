# Fit Check - Amazon-style store demo
pip install -r requirements.txt && python app.py  -> http://127.0.0.1:5000
Open any product, type your device in "Does it fit your device?". Your device is remembered; listing pages then show fit badges.
Data: DEVICES / ACCESSORIES in app.py. Rules: RULES in app.py. Integration point: GET /api/fit?accessory=<id>&q=<device text>
