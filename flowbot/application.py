from data import load_flow_targets
from data import add_target

from flask import Flask
from flask import request
from flask_cors import CORS

import json

app = Flask(__name__)
CORS(app)

@app.route('/add-tracker/', methods=['POST'])
def add_tracker():
    print(request.json)
    data = request.json#['data']

    print(data)
    add_target(data)
    return json.dumps(data)

# @app.route('/')
# def home():
#     return load_flow_targets().to_json(orient='records')

if __name__ == '__main__':
	app.run(debug=False, threaded=True, host='0.0.0.0')
