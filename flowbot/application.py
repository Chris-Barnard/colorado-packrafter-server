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
    data = request.json

    try:
        if len(data['email']) > 5:
            add_target(data)
        else:
            raise Exception('Invalid submission', data['email'])
    except Exception as e:
        raise e
    return json.dumps(data)

if __name__ == '__main__':
	app.run(debug=False, threaded=True, host='0.0.0.0')
