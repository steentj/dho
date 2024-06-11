from flask import Flask, render_template, request
from searchengine import SearchEngine

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    search_engine = SearchEngine()
    search_text = request.form['search_text']
    print(search_text)
    search_results = search_engine.get_results(query=search_text)

    return render_template('index.html', search_results=search_results, search_text=search_text)

if __name__ == '__main__':
    app.run(debug=True)