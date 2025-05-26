
from flask import Flask, render_template
import os

app = Flask(__name__, static_folder='static')

@app.route('/')
def index():
    # Список графиков в static/
    charts = [f for f in os.listdir('static') if f.endswith(('.png', '.jpg', '.jpeg'))]
    return render_template('index.html', charts=charts)

if __name__ == '__main__':
    app.run(debug=True)
