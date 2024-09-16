from flask import Flask, render_template, request
from searchengine import SearchEngine

app = Flask(__name__)
chunk_size = 'lille'
distance_function = 'cosine'
search_text = ''

@app.route('/')
def index():
    # print(f"'Index: '{search_text}', '{chunk_size}', '{distance_function}'")
    return render_template('index.html', chunk_size=chunk_size, distance_function=distance_function)

@app.route('/search', methods=['POST'])
def search():
    search_engine = SearchEngine()
    search_text = request.form['search_text']
    chunk_size = request.form.get('chunk_size')
    distance_function = request.form.get('distance_function')

    # print(f"Før søgning: '{search_text}', '{chunk_size}', '{distance_function}'")
    search_results = search_engine.get_results(search_text, chunk_size, distance_function)

    # print(f"Efter søgning: '{search_text}', '{chunk_size}', '{distance_function}'")
    return render_template('index.html', search_results=search_results, search_text=search_text, chunk_size=chunk_size, distance_function=distance_function)

if __name__ == '__main__':
    app.run(debug=True)