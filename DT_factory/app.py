from flask import Flask
from docker_start import start_docker


app = Flask(__name__)

app.add_url_rule('/api/start_docker', view_func=start_docker, methods=["GET"])


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5003, debug=True) 