import pandas as pd
import numpy as np

class DemandEngine:
    def __init__(self, df: pd.DataFrame, window: int = 7):
        """
        df must contain columns:
        - Item
        - Date
        - QuantitySold
        """
        self.df = df.copy()
        self.window = window

        if not {"Item", "Date", "QuantitySold"}.issubset(self.df.columns):
            raise ValueError("DataFrame must contain Item, Date, and QuantitySold columns.")

        self.df['Date'] = pd.to_datetime(self.df['Date'])
        self.df.sort_values(['Item', 'Date'], inplace=True)

    def calculate_sma_demand(self) -> pd.DataFrame:
        """Calculate Simple Moving Average demand for each item"""
        sma_df = (
            self.df.groupby('Item')
            .apply(lambda x: x.set_index('Date')['QuantitySold'].rolling(self.window).mean().iloc[-1])
            .reset_index(name='ForecastDemand')
        )
        return sma_df

    def calculate_average_daily_demand(self) -> pd.DataFrame:
        avg_df = (
            self.df.groupby('Item')['QuantitySold']
            .mean()
            .reset_index(name='AvgDailyDemand')
        )
        return avg_df

    def calculate_std_dev(self) -> pd.DataFrame:
        std_df = (
            self.df.groupby('Item')['QuantitySold']
            .std()
            .fillna(0)
            .reset_index(name='DemandStdDev')
        )
        return std_df

    def calculate_safety_stock(self, demand_std: pd.DataFrame, z_value: float = 1.65) -> pd.DataFrame:
        safety_df = demand_std.copy()
        safety_df['SafetyStock'] = safety_df['DemandStdDev'] * z_value
        return safety_df[['Item', 'SafetyStock']]

    def calculate_reorder_point(self, sma_demand: pd.DataFrame, safety_stock: pd.DataFrame, lead_time_days: int = 5) -> pd.DataFrame:
        reorder_df = sma_demand.merge(safety_stock, on='Item', how='left')
        reorder_df['ReorderPoint'] = reorder_df['ForecastDemand'] * lead_time_days + reorder_df['SafetyStock']
        return reorder_df[['Item', 'ForecastDemand', 'SafetyStock', 'ReorderPoint']]

    def run(self, lead_time_days: int = 5, z_value: float = 1.65) -> pd.DataFrame:
        sma_demand = self.calculate_sma_demand()
        demand_std = self.calculate_std_dev()
        safety_stock = self.calculate_safety_stock(demand_std, z_value)
        result = self.calculate_reorder_point(sma_demand, safety_stock, lead_time_days)
        return result