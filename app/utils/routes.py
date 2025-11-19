from flask import Blueprint, request, jsonify
import traceback

bp = Blueprint("main", __name__)

def register_routes(app):

    @app.before_request
    def log_request():
        app.logger.info(
            f"{request.method} {request.path} | IP: {request.remote_addr}"
        )

    @app.route("/")
    def home():
        app.logger.info("Home endpoint accessed")
        return jsonify({"message": "Hello Production!"})

    @app.route("/error")
    def error():
        try:
            1 / 0
        except Exception as e:
            app.logger.error(f"Error occurred: {e}")
            app.logger.error(traceback.format_exc())
            return "Crashed!", 500

    app.register_blueprint(bp)
