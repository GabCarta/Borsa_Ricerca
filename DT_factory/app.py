from flask import Flask
from docker_start import start_docker
from management_dt import get_user_dts, create_dt

app = Flask(__name__)

app.add_url_rule("/api/start_docker", view_func=start_docker, methods=["GET"])
app.add_url_rule("/api/create_dt", view_func=create_dt, methods=["POST"])
app.add_url_rule("/api/user_dts", view_func=get_user_dts, methods=["GET"])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003, debug=True)
