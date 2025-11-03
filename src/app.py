from flask import Flask, render_template, request, send_file, redirect, url_for
from pathlib import Path
from data_loader import load_sales
from demand_engine import compute_metrics
from viz import plot_demand_time_series, plot_stock_vs_reorder, save_bytesio_to_path

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / 'data'
OUTPUT_DIR = BASE_DIR / 'output'
DEFAULT_DATA = DATA_DIR / 'sales_data.csv'
OUTPUT_FILE = OUTPUT_DIR / 'restock_recommendations.csv'

# Ensure Flask finds the project's top-level templates/ and static/ directories
app = Flask(
    __name__,
    template_folder=str(BASE_DIR / 'templates'),
    static_folder=str(BASE_DIR / 'static'),
)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files.get('file')
        if file:
            DATA_DIR.mkdir(exist_ok=True)
            upload_path = DATA_DIR / 'uploaded_sales.csv'
            file.save(upload_path)
            return redirect(url_for('dashboard', filename='uploaded_sales.csv'))
    # Provide items and summary counts to the index template
    try:
        # prefer uploaded file if present
        uploaded = DATA_DIR / 'uploaded_sales.csv'
        data_source = uploaded if uploaded.exists() else DEFAULT_DATA
        df = load_sales(str(data_source))
        # items list
        items = sorted(df['Product'].unique().tolist()) if 'Product' in df.columns else sorted(df['Item'].unique().tolist())
        total_items = len(items)
        # compute low stock and reorder counts using compute_metrics if possible
        try:
            metrics = compute_metrics(df)
            reorder_count = int((metrics['ForecastDemand'] > 0).sum()) if 'ForecastDemand' in metrics.columns else 0
        except Exception:
            reorder_count = 0
        low_stock_count = 0
        selected_item = request.args.get('item') or (items[0] if items else None)
        current_dataset = data_source.name
    except Exception:
        items = []
        total_items = 0
        low_stock_count = 0
        reorder_count = 0
        selected_item = None
        current_dataset = DEFAULT_DATA.name

    return render_template('index.html', items=items, total_items=total_items, low_stock_count=low_stock_count, reorder_count=reorder_count, selected_item=selected_item, current_dataset=current_dataset)


@app.route('/dashboard')
def dashboard():
    # Accept either a filename (from upload) or an item selector from the index page
    filename = request.args.get('filename')
    selected_item = request.args.get('item')
    csv_path = DEFAULT_DATA if not filename else DATA_DIR / filename
    df = load_sales(str(csv_path))
    # compute demand/stock metrics
    metrics = compute_metrics(df)

    # compute template-friendly summary values
    total_stock = int(df['Current_Stock'].sum()) if 'Current_Stock' in df.columns else 0

    # derive per-item current stock (use last known/current value per product)
    if 'Product' in df.columns:
        stock_by_item = df.groupby('Product')['Current_Stock'].last()
    elif 'Item' in df.columns:
        stock_by_item = df.groupby('Item')['Current_Stock'].last()
    else:
        stock_by_item = None

    # low stock count: items where current stock < reorder point
    low_stock_count = 0
    if stock_by_item is not None and 'Item' in metrics.columns and 'ReorderPoint' in metrics.columns:
        # align item names
        metric_stock = metrics.set_index('Item')
        # intersect items
        common = stock_by_item.index.intersection(metric_stock.index)
        low_stock_count = int((stock_by_item.loc[common] < metric_stock.loc[common, 'ReorderPoint']).sum())

    predicted_total = float(metrics['ForecastDemand'].sum()) if 'ForecastDemand' in metrics.columns else 0.0

    # ensure output dir exists and save metrics
    OUTPUT_DIR.mkdir(exist_ok=True)
    metrics.to_csv(OUTPUT_FILE, index=False)

    # save chart images to static/charts so dashboard template (which references static images) can show them
    static_charts_dir = BASE_DIR / 'static' / 'charts'
    static_charts_dir.mkdir(parents=True, exist_ok=True)
    try:
        target_item = None
        if selected_item:
            target_item = selected_item
        else:
            target_item = df['Product'].unique()[0] if 'Product' in df.columns else df['Item'].unique()[0]
        buf1 = plot_demand_time_series(df, target_item)
        save_bytesio_to_path(buf1, static_charts_dir / 'inventory_trend.png')
    except Exception:
        # create an empty placeholder image if plotting fails
        try:
            buf1 = plot_demand_time_series(df, df['Product'].unique()[0])
            save_bytesio_to_path(buf1, static_charts_dir / 'inventory_trend.png')
        except Exception:
            pass

    try:
        buf2 = plot_stock_vs_reorder(metrics)
        save_bytesio_to_path(buf2, static_charts_dir / 'demand_forecast.png')
    except Exception:
        pass

    return render_template('dashboard.html', total_stock=total_stock, low_stock_count=low_stock_count, predicted_total=predicted_total)


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