import pandas as pd
from sqlalchemy import (
    create_engine, MetaData, Table, Column,
    String, Integer, Float, Boolean, Date, Time, text
)

# ---------------------------------------------------------------------------
# 1. CONFIGURE YOUR CONNECTION
# ---------------------------------------------------------------------------
DB_USER = "root"
DB_PASSWORD = "1999"
DB_HOST = "localhost"
DB_PORT = "3306"
DB_NAME = "food_delivery_db"

CONNECTION_STRING = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)


CSV_PATH = "ONLINE_FOOD_DELIVERY_FEATURE_ENGINEERED.csv"
TABLE_NAME = "online_food_delivery"

# ---------------------------------------------------------------------------
# 2. LOAD AND LIGHTLY PREPARE THE DATA
# ---------------------------------------------------------------------------
print("Step 1: Reading CSV...")
df = pd.read_csv(CSV_PATH)
print(f"Loaded {df.shape[0]} rows, {df.shape[1]} columns")

# Normalize mixed date separators (10/20/2024 and 08-12-2024 both = MM-DD-YYYY)
# then convert to a real date type for MySQL.
print("Step 2: Parsing Order_Date...")
df["Order_Date"] = pd.to_datetime(
    df["Order_Date"].str.replace("/", "-", regex=False),
    format="%m-%d-%Y"
).dt.date

# Order_Time as proper time object
df["Order_Time"] = pd.to_datetime(df["Order_Time"], format="%H:%M").dt.time

# Ensure boolean column is a real bool (CSV round-trips as True/False strings already fine)
df["Peak_Hour"] = df["Peak_Hour"].astype(bool)

# ---------------------------------------------------------------------------
# 3. DEFINE THE TABLE SCHEMA WITH PROPER DATA TYPES
# ---------------------------------------------------------------------------
print("Step 3: Defining table schema...")
engine = create_engine(CONNECTION_STRING)
metadata = MetaData()

online_food_delivery = Table(
    TABLE_NAME, metadata,
    Column("Order_ID", String(15), primary_key=True),
    Column("Customer_ID", String(15)),
    Column("Customer_Age", Integer),
    Column("Customer_Gender", String(10)),
    Column("City", String(20)),
    Column("Area", String(15)),
    Column("Restaurant_ID", String(15)),
    Column("Restaurant_Name", String(30)),
    Column("Cuisine_Type", String(20)),
    Column("Order_Date", Date),
    Column("Order_Time", Time),
    Column("Delivery_Time_Min", Integer),
    Column("Distance_km", Float),
    Column("Order_Value", Integer),
    Column("Discount_Applied", Integer),
    Column("Final_Amount", Integer),
    Column("Payment_Mode", String(15)),
    Column("Order_Status", String(15)),
    Column("Cancellation_Reason", String(30)),
    Column("Delivery_Partner_ID", String(15)),
    Column("Delivery_Rating", Integer),
    Column("Restaurant_Rating", Float),
    Column("Order_Day", String(10)),
    Column("Peak_Hour", Boolean),
    Column("Profit_Margin", Float),
    # Derived / feature-engineered columns
    Column("Order_Day_Type", String(10)),
    Column("Peak_Hour_Indicator", String(15)),
    Column("Profit_Margin_Percentage", Float),
    Column("Delivery_Performance_Category", String(15)),
    Column("Customer_Age_Group", String(10)),
)

# ---------------------------------------------------------------------------
# 4. CREATE THE TABLE (drops + recreates if it already exists)
# ---------------------------------------------------------------------------
print("Step 4: Creating table...")
with engine.connect() as conn:
    metadata.drop_all(engine, tables=[online_food_delivery])
    metadata.create_all(engine, tables=[online_food_delivery])

    # Indexes for fast filtering/reporting (scalable querying)
    conn.execute(text(f"CREATE INDEX idx_city ON {TABLE_NAME} (City)"))
    conn.execute(text(f"CREATE INDEX idx_cuisine ON {TABLE_NAME} (Cuisine_Type)"))
    conn.execute(text(f"CREATE INDEX idx_order_date ON {TABLE_NAME} (Order_Date)"))
    conn.execute(text(f"CREATE INDEX idx_customer ON {TABLE_NAME} (Customer_ID)"))
    conn.commit()
print(f"Table '{TABLE_NAME}' created with indexes on City, Cuisine_Type, Order_Date, Customer_ID.")

# ---------------------------------------------------------------------------
# 5. INSERT DATA USING SQLALCHEMY (via pandas, chunked for large datasets)
# ---------------------------------------------------------------------------
print("Step 5: Inserting data...")
df.to_sql(
    TABLE_NAME,
    con=engine,
    if_exists="append",   # table already created with correct types above
    index=False,
    chunksize=5000,        # batches for 80k+ rows
    method="multi"
)
print(f"Inserted {len(df)} rows into '{TABLE_NAME}'.")

# ---------------------------------------------------------------------------
# 6. VERIFY
# ---------------------------------------------------------------------------
print("Step 6: Verifying...")
with engine.connect() as conn:
    count = conn.execute(text(f"SELECT COUNT(*) FROM {TABLE_NAME}")).scalar()
    print(f"Row count in MySQL table: {count}")
    sample = conn.execute(text(f"SELECT * FROM {TABLE_NAME} LIMIT 3")).fetchall()
    for row in sample:
        print(row)

print("Done.")

