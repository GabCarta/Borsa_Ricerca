from flask import Flask
from management_admin import (
    statistic,
    review_parameter_request,
    get_parameter_requests,
    get_parameters,
    upload_parameters,
)
from management_user import (
    login,
    register_user,
    get_user_replicas,
    create_dt,
    get_user_dts,
    get_services,
    request_parameter,
)

app = Flask(__name__)
app.add_url_rule("/api/register_user", view_func=register_user, methods=["POST"])
app.add_url_rule("/api/login", view_func=login, methods=["POST"])
app.add_url_rule("/api/user_replicas", view_func=get_user_replicas, methods=["GET"])
app.add_url_rule("/api/create_dt", view_func=create_dt, methods=["POST"])
app.add_url_rule("/api/user_dts", view_func=get_user_dts, methods=["GET"])
app.add_url_rule("/api/services", view_func=get_services, methods=["GET"])
app.add_url_rule(
    "/api/request_parameter", view_func=request_parameter, methods=["POST"]
)
app.add_url_rule("/api/count_request", view_func=statistic, methods=["GET"])
app.add_url_rule(
    "/api/review_parameter_request",
    view_func=review_parameter_request,
    methods=["POST"],
)
app.add_url_rule(
    "/api/parameter_requests", view_func=get_parameter_requests, methods=["GET"]
)
app.add_url_rule("/api/parameters", view_func=get_parameters, methods=["GET"])
app.add_url_rule(
    "/api/upload_parameters", view_func=upload_parameters, methods=["POST"]
)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5005, debug=True)
