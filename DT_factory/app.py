from flask import Flask
from management_dt import get_user_dts, create_dt
from service_output import service_output

app = Flask(__name__)

app.add_url_rule("/api/create_dt", view_func=create_dt, methods=["POST"])
app.add_url_rule("/api/user_dt", view_func=get_user_dts, methods=["GET"])
app.add_url_rule("/api/service_output", view_func=service_output, methods=["GET"])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003, debug=True)
