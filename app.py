from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from analyzer import analyze_comments

app = Flask(__name__)
CORS(app)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.get_json()
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'Please provide a YouTube URL'})
    result = analyze_comments(url)
    return jsonify(result)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
