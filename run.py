"""Local development server:  python run.py  ->  http://127.0.0.1:5000"""
import os

from voucher import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
