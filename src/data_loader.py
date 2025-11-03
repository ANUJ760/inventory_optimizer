from pathlib import Path
import pandas as pd


def load_sales(csv_path: str):
    """
    Load and validate sales data from CSV.
    
    Required columns:
    - Date (YYYY-MM-DD)
    - Product
    - Sold_Units
    
    Optional column:
    - Current_Stock (defaults to 0 if missing)
    """
    
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {csv_path}")
    
    df = pd.read_csv(path)
    
    if "Date" not in df.columns:
        raise ValueError("CSV must contain a 'Date' column.")
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])  # remove invalid dates
    
   
    if "Product" not in df.columns:
        raise ValueError("CSV must contain a 'Product' column.")
    

    if "Sold_Units" not in df.columns:
        raise ValueError("CSV must contain a 'Sold_Units' column.")
    df["Sold_Units"] = df["Sold_Units"].fillna(0).astype(int)


    if "Current_Stock" not in df.columns:
        df["Current_Stock"] = 0
    df["Current_Stock"] = df["Current_Stock"].fillna(0).astype(int)
    
    return df