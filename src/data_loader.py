import pandas as pd
from io import BytesIO, StringIO


def load_sales_from_buffer(file_buffer):
    """
    Load and validate sales data from a file buffer (BytesIO or StringIO).
    
    Required columns:
    - Date (YYYY-MM-DD)
    - Product
    - Sold_Units
    
    Optional column:
    - Current_Stock (defaults to 0 if missing)
    """
    print("Loading data from buffer...")  # Debug log
    if isinstance(file_buffer, BytesIO):
        file_buffer.seek(0)
        content = file_buffer.read().decode('utf-8')
        df = pd.read_csv(StringIO(content))
    elif isinstance(file_buffer, StringIO):
        df = pd.read_csv(file_buffer)
    else:
        df = pd.read_csv(file_buffer)
    

    if "Date" not in df.columns:
        raise ValueError("CSV must contain a 'Date' column.")
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])  # remove invalid dates
    
    # Validate Product
    if "Product" not in df.columns:
        raise ValueError("CSV must contain a 'Product' column.")
    
    # Validate Sold_Units
    if "Sold_Units" not in df.columns:
        raise ValueError("CSV must contain a 'Sold_Units' column.")
    df["Sold_Units"] = df["Sold_Units"].fillna(0).astype(int)
    
    # Ensure Current_Stock exists
    if "Current_Stock" not in df.columns:
        df["Current_Stock"] = 0
    df["Current_Stock"] = df["Current_Stock"].fillna(0).astype(int)
    
    return df