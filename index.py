from flask import Flask, render_template, request
from searchengine import SearchEngine

app = Flask(__name__)
chunk_size = 'medium'

@app.route('/')
def index():
    return render_template('index.html', chunk_size=chunk_size)

@app.route('/search', methods=['POST'])
def search():
    search_engine = SearchEngine()
    search_text = request.form['search_text']
    chunk_size = request.form.get('chunk_size')

    print(search_text, chunk_size)
    search_results = search_engine.get_results(search_text, chunk_size)

    return render_template('index.html', search_results=search_results, search_text=search_text, chunk_size=chunk_size)

if __name__ == '__main__':
    app.run(debug=True)