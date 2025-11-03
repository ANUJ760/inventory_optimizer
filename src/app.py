from flask import Flask, render_template, request, send_file, redirect, url_for
from pathlib import Path
from data_loader import load_sales
from demand_engine import compute_metrics
from viz import plot_demand_time_series, plot_stock_vs_reorder

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / 'data'
OUTPUT_DIR = BASE_DIR / 'output'
DEFAULT_DATA = DATA_DIR / 'sales_data.csv'
OUTPUT_FILE = OUTPUT_DIR / 'restock_recommendations.csv'

app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files.get('file')
        if file:
            DATA_DIR.mkdir(exist_ok=True)
            upload_path = DATA_DIR / 'uploaded_sales.csv'
            file.save(upload_path)
            return redirect(url_for('dashboard', filename='uploaded_sales.csv'))
    return render_template('index.html')


@app.route('/dashboard')
def dashboard():
    filename = request.args.get('filename')
    csv_path = DEFAULT_DATA if not filename else DATA_DIR / filename
    df = load_sales(str(csv_path))
    metrics = compute_metrics(df)
    OUTPUT_DIR.mkdir(exist_ok=True)
    metrics.to_csv(OUTPUT_FILE, index=False)
    return render_template('dashboard.html', metrics=metrics.to_dict(orient='records'))


@app.route('/plot/demand/<product>')
def plot_demand(product):
    df = load_sales(str(DEFAULT_DATA))
    buf = plot_demand_time_series(df, product)
    return send_file(buf, mimetype='image/png')


@app.route('/plot/stock_reorder')
def plot_stock():
    df = load_sales(str(DEFAULT_DATA))
    metrics = compute_metrics(df)
    buf = plot_stock_vs_reorder(metrics)
    return send_file(buf, mimetype='image/png')


@app.route('/download')
def download():
    if OUTPUT_FILE.exists():
        return send_file(OUTPUT_FILE, as_attachment=True)
    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    app.run(debug=True)