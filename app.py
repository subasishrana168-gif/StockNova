import sqlite3
from pathlib import Path
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

# -------------------- Configuration --------------------
st.set_page_config(
    page_title="StockNova Inventory",
    page_icon="📦",
    layout="wide",
)

DB_PATH = Path(__file__).with_name("inventory.db")


# -------------------- Database helpers --------------------
def get_connection():
    return sqlite3.connect(DB_PATH, timeout=10)


def setup_database():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                supplier TEXT DEFAULT '',
                price REAL NOT NULL DEFAULT 0,
                quantity INTEGER NOT NULL DEFAULT 0,
                reorder_level INTEGER NOT NULL DEFAULT 5,
                location TEXT DEFAULT 'Main Store',
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT NOT NULL,
                product_name TEXT NOT NULL,
                movement_type TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                note TEXT DEFAULT '',
                created_at TEXT NOT NULL
            )
        """)
        count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        if count == 0:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            samples = [
                ("TECH-001", "Wireless Mouse", "Electronics", "Nova Supplies", 599, 34, 8, "Shelf A1"),
                ("TECH-002", "Mechanical Keyboard", "Electronics", "KeyWorks", 1899, 12, 5, "Shelf A2"),
                ("TECH-003", "USB-C Hub", "Accessories", "Nova Supplies", 1299, 7, 6, "Shelf A3"),
                ("STAT-001", "A4 Notebook", "Stationery", "Campus Wholesale", 65, 80, 20, "Shelf B1"),
                ("TECH-004", "Laptop Stand", "Accessories", "ErgoStore", 899, 4, 5, "Shelf A4"),
                ("STAT-002", "Whiteboard Marker", "Stationery", "Campus Wholesale", 35, 18, 10, "Shelf B2"),
                ("TECH-005", "HD Webcam", "Electronics", "VisionTech", 2499, 0, 3, "Shelf A5"),
            ]
            conn.executemany("""
                INSERT INTO products
                (sku, name, category, supplier, price, quantity,
                 reorder_level, location, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [row + (now,) for row in samples])


def load_products():
    with get_connection() as conn:
        return pd.read_sql_query(
            "SELECT * FROM products ORDER BY name", conn
        )


def load_movements():
    with get_connection() as conn:
        return pd.read_sql_query("""
            SELECT created_at AS 'Date & Time',
                   sku AS SKU,
                   product_name AS Product,
                   movement_type AS Movement,
                   quantity AS Quantity,
                   note AS Note
            FROM movements
            ORDER BY id DESC
        """, conn)


def create_product(sku, name, category, supplier, price,
                   quantity, reorder_level, location):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO products
            (sku, name, category, supplier, price, quantity,
             reorder_level, location, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sku.strip().upper(), name.strip(), category, supplier.strip(),
            float(price), int(quantity), int(reorder_level),
            location.strip(), now
        ))


def record_movement(product_id, movement_type, quantity, note):
    quantity = int(quantity)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        product = conn.execute(
            "SELECT * FROM products WHERE id = ?", (int(product_id),)
        ).fetchone()

        if product is None:
            raise ValueError("Product not found. Refresh and try again.")

        current_quantity = int(product[6])
        if movement_type == "Stock Out" and quantity > current_quantity:
            raise ValueError(
                f"Insufficient stock. Available quantity: {current_quantity}."
            )

        if movement_type == "Stock In":
            new_quantity = current_quantity + quantity
        else:
            new_quantity = current_quantity - quantity

        conn.execute("""
            UPDATE products SET quantity = ?, updated_at = ?
            WHERE id = ?
        """, (new_quantity, now, int(product_id)))

        conn.execute("""
            INSERT INTO movements
            (sku, product_name, movement_type, quantity, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            product[1], product[2], movement_type,
            quantity, note.strip(), now
        ))


def delete_product(product_id):
    with get_connection() as conn:
        product = conn.execute(
            "SELECT sku FROM products WHERE id = ?", (int(product_id),)
        ).fetchone()
        if product:
            conn.execute("DELETE FROM movements WHERE sku = ?", (product[0],))
            conn.execute("DELETE FROM products WHERE id = ?", (int(product_id),))


# -------------------- Visual design --------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
.stApp {
    background: radial-gradient(ellipse at 8% 0%, #1a2d52 0%, transparent 36%),
                radial-gradient(ellipse at 95% 10%, #103b40 0%, transparent 30%),
                #080d19;
    color: #eef3ff;
    font-family: 'DM Sans', sans-serif;
}
.block-container { max-width: 1450px; padding-top: 1.5rem; }
h1, h2, h3 { font-family: 'Space Grotesk', sans-serif !important; }
[data-testid="stSidebar"] { background: #0c1528; border-right: 1px solid #263653; }
[data-testid="stMetric"] {
    background: linear-gradient(135deg, #172642, #101a2d);
    border: 1px solid #2a3d5c; border-radius: 16px;
    padding: 16px; animation: rise .45s ease both;
    transition: transform .2s ease, border-color .2s ease;
}
[data-testid="stMetric"]:hover { transform: translateY(-3px); border-color: #56e5d2; }
[data-testid="stMetricLabel"] { color: #aabbd7 !important; }
[data-testid="stMetricValue"] { color: #ffffff !important; }
.hero {
    padding: 28px; border-radius: 22px; margin-bottom: 22px;
    border: 1px solid #354c76;
    background: linear-gradient(115deg, #1a2c50, #10233a 65%, #10373b);
    animation: rise .6s ease both;
}
.kicker { color: #6ce9d8; font-size: 12px; letter-spacing: 3px; font-weight: 700; }
.hero-title { color: white; font-size: 38px; font-weight: 700; line-height: 1.12; margin: 10px 0; }
.hero-sub { color: #bdcce5; line-height: 1.65; }
.stButton > button, .stDownloadButton > button {
    background: linear-gradient(100deg, #167f83, #315eb3);
    color: white; border: 1px solid #438f9a; border-radius: 10px;
    min-height: 40px; font-weight: 700;
}
.stButton > button:hover, .stDownloadButton > button:hover {
    border-color: #6ce9d8; color: white;
}
div[data-testid="stForm"] {
    border: 1px solid #2a3d5c; border-radius: 14px;
    padding: 18px; background: rgba(16,26,45,.7);
}
@keyframes rise {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
}
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation: none !important; transition: none !important; }
}
</style>
""", unsafe_allow_html=True)

setup_database()

# -------------------- Navigation --------------------
with st.sidebar:
    st.title("📦 StockNova")
    st.caption("SMART INVENTORY MANAGEMENT")
    page = st.radio(
        "NAVIGATION",
        ["Dashboard", "Products", "Stock Movement", "Reports", "Project Guide"]
    )
    st.divider()
    st.caption("Python • SQLite • Streamlit • Plotly")
    st.caption("Local database storage")

st.markdown("""
<div class="hero">
  <div class="kicker">INVENTORY INTELLIGENCE</div>
  <div class="hero-title">StockNova<br>Control every item.</div>
  <div class="hero-sub">Track products, manage stock quantities, detect shortages,
  and turn inventory data into clear business decisions.</div>
</div>
""", unsafe_allow_html=True)

products = load_products()
if not products.empty:
    products["stock_value"] = products["price"] * products["quantity"]
    low_stock = products[
        (products["quantity"] > 0) &
        (products["quantity"] <= products["reorder_level"])
    ]
    out_stock = products[products["quantity"] == 0]
else:
    low_stock = products.copy()
    out_stock = products.copy()

# -------------------- Dashboard --------------------
if page == "Dashboard":
    st.subheader("Inventory overview")
    a, b, c, d = st.columns(4)
    a.metric("Products tracked", len(products))
    b.metric("Units in stock", f"{int(products['quantity'].sum()):,}" if not products.empty else "0")
    c.metric("Inventory value", f"₹{products['stock_value'].sum():,.0f}" if not products.empty else "₹0")
    d.metric("Need attention", len(low_stock) + len(out_stock))

    left, right = st.columns(2)
    with left:
        st.subheader("Stock by category")
        if not products.empty:
            category_data = products.groupby("category", as_index=False)["quantity"].sum()
            fig = px.bar(
                category_data, x="category", y="quantity", color="category",
                text="quantity", template="plotly_dark",
                color_discrete_sequence=["#56e5d2", "#648bff", "#b58aff", "#ffbf69"]
            )
            fig.update_layout(
                height=330, showlegend=False,
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                xaxis_title="", yaxis_title="Units"
            )
            st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("Stock health")
        if not products.empty:
            healthy_count = len(products) - len(low_stock) - len(out_stock)
            health = pd.DataFrame({
                "Status": ["Healthy", "Low stock", "Out of stock"],
                "Products": [healthy_count, len(low_stock), len(out_stock)]
            })
            fig = px.pie(
                health, names="Status", values="Products", hole=0.65,
                template="plotly_dark",
                color="Status",
                color_discrete_map={
                    "Healthy": "#56e5d2",
                    "Low stock": "#ffbf69",
                    "Out of stock": "#ff6b83"
                }
            )
            fig.update_layout(
                height=330, paper_bgcolor="rgba(0,0,0,0)",
                legend=dict(orientation="h", y=-0.1)
            )
            st.plotly_chart(fig, use_container_width=True)

    st.subheader("Inventory alerts")
    if not out_stock.empty:
        st.error("Out of stock: " + ", ".join(out_stock["name"].tolist()))
    if not low_stock.empty:
        st.warning(f"{len(low_stock)} product(s) are at or below their reorder level.")
        st.dataframe(
            low_stock[["sku", "name", "quantity", "reorder_level"]].rename(columns={
                "sku": "SKU", "name": "Product",
                "quantity": "Available", "reorder_level": "Reorder at"
            }),
            use_container_width=True, hide_index=True
        )
    if low_stock.empty and out_stock.empty:
        st.success("All products are above their reorder levels.")

    st.subheader("Recent activity")
    movements = load_movements()
    if movements.empty:
        st.info("No stock movements recorded yet.")
    else:
        st.dataframe(movements.head(6), use_container_width=True, hide_index=True)

# -------------------- Products --------------------
elif page == "Products":
    st.subheader("Product catalogue")

    with st.expander("➕ Add a product", expanded=True):
        with st.form("product_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            sku = c1.text_input("SKU / Product code *")
            name = c2.text_input("Product name *")
            category = c3.selectbox(
                "Category",
                ["Electronics", "Accessories", "Stationery", "Food & Beverage", "Clothing", "Other"]
            )
            c4, c5, c6 = st.columns(3)
            supplier = c4.text_input("Supplier")
            price = c5.number_input("Unit price (₹)", min_value=0.0, value=100.0, step=10.0)
            quantity = c6.number_input("Opening quantity", min_value=0, value=0, step=1)
            c7, c8 = st.columns(2)
            reorder = c7.number_input("Reorder threshold", min_value=0, value=5, step=1)
            location = c8.text_input("Storage location", value="Main Store")
            submitted = st.form_submit_button("Save product", use_container_width=True)

            if submitted:
                if not sku.strip() or not name.strip():
                    st.error("SKU and product name are required.")
                else:
                    try:
                        create_product(
                            sku, name, category, supplier, price,
                            int(quantity), int(reorder), location
                        )
                        st.success("Product added successfully.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("That SKU already exists. Please enter a unique SKU.")

    search = st.text_input("🔎 Search products", placeholder="Name, SKU, category, supplier, location")
    categories = ["All categories"] + sorted(products["category"].unique().tolist()) if not products.empty else ["All categories"]
    selected_category = st.selectbox("Filter category", categories)
    view = products.copy()

    if search:
        mask = view.astype(str).apply(
            lambda col: col.str.contains(search, case=False, na=False)
        ).any(axis=1)
        view = view[mask]
    if selected_category != "All categories":
        view = view[view["category"] == selected_category]

    display = view[[
        "sku", "name", "category", "supplier", "price",
        "quantity", "reorder_level", "location"
    ]].rename(columns={
        "sku": "SKU", "name": "Product", "category": "Category",
        "supplier": "Supplier", "price": "Price (₹)",
        "quantity": "Quantity", "reorder_level": "Reorder level",
        "location": "Location"
    })
    st.dataframe(display, use_container_width=True, hide_index=True)

    with st.expander("Delete a product"):
        if products.empty:
            st.info("There are no products to delete.")
        else:
            options = {
                f"{row['sku']} — {row['name']}": int(row["id"])
                for _, row in products.iterrows()
            }
            selected = st.selectbox("Select product to delete", list(options.keys()))
            confirm = st.checkbox("I understand this permanently deletes the product and its movement history.")
            if st.button("Delete selected product"):
                if confirm:
                    delete_product(options[selected])
                    st.success("Product deleted.")
                    st.rerun()
                else:
                    st.warning("Please confirm deletion first.")

# -------------------- Stock movements --------------------
elif page == "Stock Movement":
    st.subheader("Record stock in or stock out")
    st.write("Each successful movement updates stock and adds a transaction record.")

    if products.empty:
        st.info("Add a product before recording stock movements.")
    else:
        options = {
            f"{row['sku']} — {row['name']} (available: {row['quantity']})": int(row["id"])
            for _, row in products.iterrows()
        }
        with st.form("movement_form"):
            selected = st.selectbox("Product", list(options.keys()))
            movement_type = st.radio("Movement type", ["Stock In", "Stock Out"], horizontal=True)
            qty = st.number_input("Quantity", min_value=1, value=1, step=1)
            note = st.text_input("Reference or note")
            submitted = st.form_submit_button("Confirm movement", use_container_width=True)
            if submitted:
                try:
                    record_movement(options[selected], movement_type, int(qty), note)
                    st.success("Stock movement recorded.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))

    st.subheader("Movement history")
    movements = load_movements()
    if movements.empty:
        st.info("No movements recorded yet.")
    else:
        st.dataframe(movements, use_container_width=True, hide_index=True)
        st.download_button(
            "Download movement history CSV",
            movements.to_csv(index=False).encode("utf-8"),
            file_name="stocknova_movements.csv",
            mime="text/csv"
        )

# -------------------- Reports --------------------
elif page == "Reports":
    st.subheader("Reports and analytics")
    if products.empty:
        st.info("Add products to create reports.")
    else:
        report = products.copy()
        report["stock_value"] = report["price"] * report["quantity"]
        a, b, c = st.columns(3)
        a.metric("Total stock value", f"₹{report['stock_value'].sum():,.2f}")
        b.metric("Average units per product", f"{report['quantity'].mean():.1f}")
        c.metric("Categories", int(report["category"].nunique()))

        category_value = report.groupby("category", as_index=False)["stock_value"].sum()
        fig = px.bar(
            category_value, x="category", y="stock_value", color="category",
            text_auto=".2s", template="plotly_dark",
            color_discrete_sequence=["#56e5d2", "#648bff", "#b58aff", "#ffbf69"]
        )
        fig.update_layout(
            height=350, showlegend=False,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis_title="", yaxis_title="Inventory value (₹)"
        )
        st.plotly_chart(fig, use_container_width=True)

        st.download_button(
            "Download full inventory CSV",
            report.to_csv(index=False).encode("utf-8"),
            file_name="stocknova_inventory.csv",
            mime="text/csv"
        )
        low_report = report[report["quantity"] <= report["reorder_level"]]
        st.download_button(
            "Download low-stock CSV",
            low_report.to_csv(index=False).encode("utf-8"),
            file_name="stocknova_low_stock.csv",
            mime="text/csv"
        )

# -------------------- Project guide --------------------
elif page == "Project Guide":
    st.subheader("Project overview")
    st.markdown("""
    **StockNova — Smart Inventory Management System**

    **Objective:** Track products and stock quantities accurately, reduce stock-outs,
    and maintain a history of inventory movements.

    **Main features**
    - Product catalogue with unique SKUs.
    - Stock-in and stock-out operations.
    - Validation to prevent stock from becoming negative.
    - Low-stock and out-of-stock alerts.
    - Interactive charts and inventory valuation.
    - Transaction history and CSV reports.
    - SQLite persistence between application runs.

    **Technology stack:** Python, Streamlit, SQLite, Pandas, Plotly and CSS.

    **Database tables**
    - `products`: current product details and quantities.
    - `movements`: stock-in and stock-out history.

    **Suggested demonstration**
    1. Add a product with opening stock of 10.
    2. Record Stock In of 5; the balance becomes 15.
    3. Record Stock Out of 3; the balance becomes 12.
    4. Attempt to remove more than 12 units and show the validation message.
    5. Show the dashboard and download a report.

    **Current limitations:** This is a local classroom prototype. It does not include
    user authentication, barcode scanning, cloud synchronisation, or multi-user access.
    """)

st.divider()
st.caption("StockNova • Python Inventory Management System")
