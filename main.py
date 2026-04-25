import os
import sys

# Print sys.path for debugging
print("PYTHONPATH:", sys.path)

try:
    from api.index import app
except Exception as e:
    print("CRITICAL IMPORT ERROR:", str(e))
    raise e

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
