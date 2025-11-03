import pandas as pd
import matplotlib.pyplot as plt

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