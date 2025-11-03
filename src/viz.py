import pandas as pd
import matplotlib.pyplot as plt
import io
from pathlib import Path

plt.style.use('dark_background')

class Visualizer:
    def __init__(self, df: pd.DataFrame, forecast_df: pd.DataFrame = None):
        self.df = df.copy()
        self.forecast_df = forecast_df.copy() if forecast_df is not None else None

    def plot_demand_trend(self, item: str):
        data = self.df[self.df["Item"] == item].sort_values("Date")
        if data.empty:
            raise ValueError(f"No data found for item: {item}")
        plt.figure()
        plt.plot(data["Date"], data["QuantitySold"])
        plt.xlabel("Date")
        plt.ylabel("Quantity Sold")
        plt.title(f"Demand Trend for {item}")
        return plt

    def plot_forecast_accuracy(self, item: str):
        if self.forecast_df is None:
            raise ValueError("forecast_df required for forecast accuracy plot.")
        actual = self.df[self.df["Item"] == item].sort_values("Date")
        forecast = self.forecast_df[self.forecast_df["Item"] == item].sort_values("Date")
        merged = pd.merge(actual, forecast, on=["Item", "Date"], how="inner")
        if merged.empty:
            raise ValueError(f"Forecast and actual data do not align for item: {item}")
        plt.figure()
        plt.plot(merged["Date"], merged["QuantitySold"])
        plt.plot(merged["Date"], merged["Forecast"])
        plt.xlabel("Date")
        plt.ylabel("Units")
        plt.title(f"Forecast vs Actual for {item}")
        return plt


def _fig_to_bytesio(fig) -> io.BytesIO:
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    return buf


def plot_demand_time_series(df: pd.DataFrame, product: str) -> io.BytesIO:
    """Return a PNG BytesIO of the demand time series for `product`.
    Accepts DataFrame with either Product/Item and Sold_Units/QuantitySold.
    """
    df_copy = df.copy()
    if 'Product' in df_copy.columns and 'Sold_Units' in df_copy.columns:
        df_copy = df_copy.rename(columns={'Product': 'Item', 'Sold_Units': 'QuantitySold'})

    data = df_copy[df_copy['Item'] == product].sort_values('Date')
    if data.empty:
        # create a small empty figure with a message
        fig = plt.figure()
        plt.text(0.5, 0.5, f'No data for {product}', ha='center')
        return _fig_to_bytesio(fig)

    fig = plt.figure()
    plt.plot(data['Date'], data['QuantitySold'], marker='o')
    plt.xlabel('Date')
    plt.ylabel('Quantity Sold')
    plt.title(f'Demand Trend for {product}')
    plt.tight_layout()
    return _fig_to_bytesio(fig)


def plot_stock_vs_reorder(metrics_df: pd.DataFrame) -> io.BytesIO:
    """Return a PNG BytesIO comparing ForecastDemand and ReorderPoint per Item.
    metrics_df expected to contain columns: Item, ForecastDemand, ReorderPoint
    """
    df = metrics_df.copy()
    if 'Item' not in df.columns:
        # try common alternatives
        if 'Product' in df.columns:
            df = df.rename(columns={'Product': 'Item'})

    df = df.sort_values('ForecastDemand', ascending=False).head(20)
    fig = plt.figure(figsize=(10, 6))
    x = range(len(df))
    plt.bar(x, df['ForecastDemand'], label='ForecastDemand', alpha=0.7)
    if 'ReorderPoint' in df.columns:
        plt.bar(x, df['ReorderPoint'], label='ReorderPoint', alpha=0.4)
    plt.xticks(x, df['Item'], rotation=45, ha='right')
    plt.ylabel('Units')
    plt.title('Forecast Demand vs Reorder Point')
    plt.legend()
    plt.tight_layout()
    return _fig_to_bytesio(fig)


def save_bytesio_to_path(buf: io.BytesIO, path: str | Path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'wb') as f:
        f.write(buf.getbuffer())