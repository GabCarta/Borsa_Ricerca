from flask import Flask

from check_consumi_ind import calcola_consumi

app = Flask(__name__)
app.add_url_rule('/api/check_consumi', view_func=calcola_consumi, methods=["GET"])


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)