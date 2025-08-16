from app.routes import create_app
import os

app = create_app()

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5001)),
        debug=os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    )

