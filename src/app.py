from flask import Flask, render_template, request, send_file, redirect, url_for, session
from pathlib import Path
from io import BytesIO
import os
import tempfile
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from data_loader import load_sales_from_buffer
from demand_engine import compute_metrics
from viz import plot_demand_time_series, plot_stock_vs_reorder, save_bytesio_to_path

BASE_DIR = Path(__file__).resolve().parents[1]

# Set up Flask app with session support
app = Flask(
    __name__,
    template_folder=str(BASE_DIR / 'templates'),
    static_folder=str(BASE_DIR / 'static'),
)

# Set a fixed secret key for development (change this in production!)
app.config['SECRET_KEY'] = 'dev-secret-key-inventory-optimizer'


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files.get('file')
        if file:
            try:
                # Read and validate the file immediately
                file_content = file.read()
                file_buffer = BytesIO(file_content)
                # Verify we can load and process the data
                df = load_sales_from_buffer(file_buffer)

                # If successful, write to a temp file and store path in session
                # Remove previous temp file if present
                prev = session.get('uploaded_path')
                if prev:
                    try:
                        if os.path.exists(prev):
                            os.remove(prev)
                    except Exception:
                        logger.debug('Unable to remove previous temp file', exc_info=True)

                tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.csv')
                tmp.write(file_content)
                tmp.flush()
                tmp.close()
                session['uploaded_path'] = tmp.name
                session['filename'] = file.filename
                return redirect(url_for('dashboard'))
            except Exception as e:
                # If there's an error, clear any previous data
                session.pop('uploaded_path', None)
                session.pop('filename', None)
                logger.error(f"Error processing file: {e}")
                return f"Error processing file: {str(e)}"

    # Check if we have data in session
    if 'uploaded_path' not in session:
        # no data available yet
        items = []
        total_items = 0
        low_stock_count = 0
        reorder_count = 0
        selected_item = None
        current_dataset = None
        return render_template('index.html', items=items, total_items=total_items, 
                            low_stock_count=low_stock_count, reorder_count=reorder_count, 
                            selected_item=selected_item, current_dataset=current_dataset)

    # Load uploaded dataset from temp file path saved in session
    uploaded_path = session.get('uploaded_path')
    if not uploaded_path or not os.path.exists(uploaded_path):
        # lost file, redirect to upload
        session.pop('uploaded_path', None)
        session.pop('filename', None)
        return redirect(url_for('index'))
    with open(uploaded_path, 'rb') as f:
        file_buffer = BytesIO(f.read())
    df = load_sales_from_buffer(file_buffer)
    
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
    current_dataset = "uploaded_data"

    return render_template('index.html', items=items, total_items=total_items, low_stock_count=low_stock_count, reorder_count=reorder_count, selected_item=selected_item, current_dataset=current_dataset)


@app.route('/dashboard')
def dashboard():
    # Check if we have data in session
    if 'uploaded_path' not in session:
        return redirect(url_for('index'))

    selected_item = request.args.get('item')
    
    # Load data from session
    uploaded_path = session.get('uploaded_path')
    if not uploaded_path or not os.path.exists(uploaded_path):
        session.pop('uploaded_path', None)
        session.pop('filename', None)
        return redirect(url_for('index'))
    with open(uploaded_path, 'rb') as f:
        file_buffer = BytesIO(f.read())
    df = load_sales_from_buffer(file_buffer)
    
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

    # save chart images to static/charts so dashboard template can show them
    static_charts_dir = BASE_DIR / 'static' / 'charts'
    static_charts_dir.mkdir(parents=True, exist_ok=True)
    # Create timestamped chart filenames to avoid browser caching
    import time
    ts = int(time.time())
    inv_name = None
    fore_name = None
    try:
        target_item = selected_item if selected_item else (df['Product'].unique()[0] if 'Product' in df.columns else df['Item'].unique()[0])
        buf1 = plot_demand_time_series(df, target_item)
        inv_name = f'inventory_trend_{ts}.png'
        save_bytesio_to_path(buf1, static_charts_dir / inv_name)
    except Exception:
        # fallback: attempt to save a generic inventory_trend.png
        try:
            buf1 = plot_demand_time_series(df, df['Product'].unique()[0])
            inv_name = 'inventory_trend.png'
            save_bytesio_to_path(buf1, static_charts_dir / inv_name)
        except Exception:
            inv_name = None

    try:
        buf2 = plot_stock_vs_reorder(metrics)
        fore_name = f'demand_forecast_{ts}.png'
        save_bytesio_to_path(buf2, static_charts_dir / fore_name)
    except Exception:
        fore_name = None

    return render_template('dashboard.html', total_stock=total_stock, low_stock_count=low_stock_count, predicted_total=predicted_total, inventory_chart=inv_name, forecast_chart=fore_name)


@app.route('/plot/demand/<product>')
def plot_demand(product):
    if 'uploaded_path' not in session:
        return redirect(url_for('index'))
    uploaded_path = session.get('uploaded_path')
    if not uploaded_path or not os.path.exists(uploaded_path):
        session.pop('uploaded_path', None)
        session.pop('filename', None)
        return redirect(url_for('index'))
    with open(uploaded_path, 'rb') as f:
        file_buffer = BytesIO(f.read())
    df = load_sales_from_buffer(file_buffer)
    buf = plot_demand_time_series(df, product)
    return send_file(buf, mimetype='image/png')


@app.route('/plot/stock_reorder')
def plot_stock():
    if 'uploaded_path' not in session:
        return redirect(url_for('index'))
    uploaded_path = session.get('uploaded_path')
    if not uploaded_path or not os.path.exists(uploaded_path):
        session.pop('uploaded_path', None)
        session.pop('filename', None)
        return redirect(url_for('index'))
    with open(uploaded_path, 'rb') as f:
        file_buffer = BytesIO(f.read())
    df = load_sales_from_buffer(file_buffer)
    metrics = compute_metrics(df)
    buf = plot_stock_vs_reorder(metrics)
    return send_file(buf, mimetype='image/png')


@app.route('/download')
def download():
    if 'uploaded_path' not in session:
        return redirect(url_for('index'))
    uploaded_path = session.get('uploaded_path')
    if not uploaded_path or not os.path.exists(uploaded_path):
        session.pop('uploaded_path', None)
        session.pop('filename', None)
        return redirect(url_for('index'))
    with open(uploaded_path, 'rb') as f:
        file_buffer = BytesIO(f.read())
    df = load_sales_from_buffer(file_buffer)
    metrics = compute_metrics(df)
    
    # Create recommendations file in memory
    output_buffer = BytesIO()
    metrics.to_csv(output_buffer, index=False)
    output_buffer.seek(0)
    
    return send_file(
        output_buffer,
        mimetype='text/csv',
        as_attachment=True,
        download_name='restock_recommendations.csv'
    )


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)