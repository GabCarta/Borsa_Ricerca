from flask import Flask
from management_user import login, register_user, link_replica, get_user_replicas, create_dt, get_user_dts, get_services

app = Flask(__name__)
app.add_url_rule('/api/register_user', view_func=register_user, methods=['POST'])
app.add_url_rule('/api/login', view_func=login, methods=['POST'])
app.add_url_rule('/api/link_replica', view_func=link_replica, methods=['POST'])
app.add_url_rule('/api/user_replicas', view_func=get_user_replicas, methods=['GET'])
app.add_url_rule('/api/create_dt', view_func=create_dt, methods=['POST'])
app.add_url_rule('/api/user_dts', view_func=get_user_dts, methods=['GET'])
app.add_url_rule('/api/services', view_func=get_services, methods=['GET'])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5005, debug=True)