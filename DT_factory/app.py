from flask import Flask
from management_dt import (
    create_dt,
    create_user_namespace,
    delete_dt,
    delete_user_namespace,
    get_dt,
    get_public_dt,
    get_public_dts,
    get_user_dts,
    service_api,
    set_visibility,
    start_dt,
    stop_dt,
)
from service_catalog import get_catalog
from service_requests import (
    admin_catalog,
    check_service,
    create_request,
    delete_request,
    get_template,
    list_requests,
    review_request,
    set_service_active,
)

app = Flask(__name__)

app.add_url_rule("/api/service_catalog", view_func=get_catalog, methods=["GET"])
# servizi proposti dagli utenti (service_requests.py)
app.add_url_rule("/api/service_template", view_func=get_template, methods=["GET"])
app.add_url_rule("/api/service_requests/check", view_func=check_service, methods=["POST"])
app.add_url_rule("/api/service_requests", view_func=create_request, methods=["POST"])
app.add_url_rule("/api/service_requests", view_func=list_requests, methods=["GET"])
app.add_url_rule("/api/service_requests/<request_id>", view_func=delete_request, methods=["DELETE"])
app.add_url_rule("/api/service_requests/<request_id>/review", view_func=review_request, methods=["POST"])
app.add_url_rule("/api/admin/service_catalog", view_func=admin_catalog, methods=["GET"])
app.add_url_rule("/api/admin/service_catalog/<service_id>", view_func=set_service_active, methods=["PUT"])
app.add_url_rule("/api/create_dt", view_func=create_dt, methods=["POST"])
app.add_url_rule("/api/user_dt", view_func=get_user_dts, methods=["GET"])
app.add_url_rule("/api/dt/<dt_id>", view_func=get_dt, methods=["GET"])
app.add_url_rule("/api/dt/<dt_id>", view_func=delete_dt, methods=["DELETE"])
app.add_url_rule("/api/public_dt", view_func=get_public_dts, methods=["GET"])
app.add_url_rule("/api/public_dt/<dt_id>", view_func=get_public_dt, methods=["GET"])
app.add_url_rule("/api/dt/<dt_id>/visibility", view_func=set_visibility, methods=["PUT"])
app.add_url_rule("/api/dt/<dt_id>/start", view_func=start_dt, methods=["POST"])
app.add_url_rule("/api/dt/<dt_id>/stop", view_func=stop_dt, methods=["POST"])
app.add_url_rule(
    "/api/dt/<dt_id>/service/<instance_id>/<action>",
    view_func=service_api,
    methods=["GET", "POST"],
)
app.add_url_rule("/api/namespace", view_func=create_user_namespace, methods=["POST"])
app.add_url_rule(
    "/api/namespace/<user_id>", view_func=delete_user_namespace, methods=["DELETE"]
)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003, debug=True)
