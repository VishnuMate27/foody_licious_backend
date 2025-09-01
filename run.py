from app.routes import create_app
import os

app = create_app()

@app.route("/")
def home():
    return "Hello from Flask on Hugging Face!"