import os
import sys
import traceback
from flask import Flask

dummy_app = Flask(__name__)
error_message = None

try:
    # Try to import the real app
    from api.index import app as real_app
    app = real_app
except Exception as e:
    # If it fails, capture the error and use the dummy app
    error_message = traceback.format_exc()
    print("CRITICAL IMPORT ERROR:\n" + error_message)
    app = dummy_app

@dummy_app.route('/', methods=['GET', 'POST'])
def index():
    if error_message:
        return f"<h1>Deployment Error</h1><pre>{error_message}</pre>"
    return "Dummy app loaded, but error_message is None? This shouldn't happen."

@dummy_app.route('/<path:path>', methods=['GET', 'POST'])
def catch_all(path):
    if error_message:
        return f"<h1>Deployment Error</h1><pre>{error_message}</pre>"
    return "Dummy app loaded."

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
