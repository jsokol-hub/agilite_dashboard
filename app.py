import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, html, dcc
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
from datetime import datetime, timedelta
import json

# Import database modules
from database import db_manager
from config import DB_CONFIG

# Initialize the Dash app
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server # Expose the server variable for Gunicorn

def load_latest_data():
    """Load the most recent data from the database"""
    try:
        df = db_manager.get_latest_products()
        return df
    except Exception as e:
        print(f"Error loading data from database: {str(e)}")
        return pd.DataFrame()

def process_stock_history():
    """
    Fetch raw stock data and process it using pandas to create historical analysis.
    This moves the complex aggregation logic from SQL to Python.
    """
    raw_df = db_manager.get_stock_history_raw_data()

    if raw_df.empty:
        return []

    # Ensure timestamp is in datetime format
    raw_df['processing_timestamp'] = pd.to_datetime(raw_df['processing_timestamp'])

    # Create a 'date' column truncated to the hour for grouping
    raw_df['date'] = raw_df['processing_timestamp'].dt.floor('H')
    
    # Filter for 'In Stock' items for category analysis
    in_stock_df = raw_df[raw_df['stock_status'] == 'In Stock'].copy()
    
    # Calculate total 'In Stock' items per hour
    in_stock_by_hour = in_stock_df.groupby('date').size().reset_index(name='in_stock')

    # Calculate category counts per hour
    category_counts_by_hour = in_stock_df.groupby(['date', 'category']).size().reset_index(name='count')
    
    # Pivot to get categories as columns, then convert to a dictionary for each hour
    category_pivot = category_counts_by_hour.pivot_table(index='date', columns='category', values='count', fill_value=0)
    category_counts_dict = category_pivot.to_dict('index')

    # Merge the aggregated data
    final_history = in_stock_by_hour.copy()
    final_history['category_counts'] = final_history['date'].map(category_counts_dict)
    
    # Ensure category_counts is never NaN/NaT
    final_history['category_counts'].fillna({}, inplace=True)
    
    return final_history.to_dict('records')

def calculate_high_demand_products(df):
    """
    Analyzes product history to find items that frequently go out of stock.
    Returns a sorted DataFrame of high-demand products.
    """
    if df.empty or len(df['processing_timestamp'].unique()) < 2:
        # Need at least two different timestamps (sessions) to compare
        return pd.DataFrame(columns=['title', 'url', 'category', 'demand_score'])

    # Sort by title and timestamp to ensure correct order for status change detection
    df = df.sort_values(by=['title', 'processing_timestamp'])
    
    # Get the previous stock status for each product
    df['prev_stock_status'] = df.groupby('title')['stock_status'].shift(1)
    
    # Identify transitions from 'In Stock' to 'Out of Stock' (a likely sale)
    df['sold_out'] = ((df['prev_stock_status'] == 'In Stock') & (df['stock_status'] == 'Out of Stock'))
    
    # Calculate the demand score for each product
    demand_scores = df.groupby('title')['sold_out'].sum().reset_index(name='demand_score')
    
    # Get the latest details for each product (URL, category)
    latest_products = df.loc[df.groupby('title')['processing_timestamp'].idxmax()]
    
    # Merge scores with product details
    high_demand_df = pd.merge(demand_scores, latest_products[['title', 'url', 'category']], on='title')
    
    # Sort by the highest demand and return only products that have sold out at least once
    high_demand_df = high_demand_df.sort_values(by='demand_score', ascending=False)
    
    return high_demand_df[high_demand_df['demand_score'] > 0]

def create_high_demand_card(high_demand_df, latest_products_df):
    """
    Creates an adaptive card.
    - If there's enough history, it shows "High-Demand Products" based on sales velocity.
    - If not, it shows "Immediate Attention: Currently Out of Stock" based on the latest data.
    """
    # Mode 1: We have historical data to show top sellers
    if not high_demand_df.empty:
        card_header = "🏆 High-Demand Products (Likely Top-Sellers)"
        table_header = [html.Thead(html.Tr([html.Th("#"), html.Th("Product"), html.Th("Category"), html.Th("Demand Score")]))]
        
        table_rows = []
        for i, row in enumerate(high_demand_df.head(10).itertuples(), 1): # Show top 10
            table_rows.append(
                html.Tr([
                    html.Td(f"{i}"),
                    html.Td(html.A(row.title, href=row.url, target="_blank", rel="noopener noreferrer")),
                    html.Td(row.category),
                    html.Td(html.Span(f"{int(row.demand_score)} times sold out", className="badge bg-success"))
                ])
            )
        table_body = [html.Tbody(table_rows)]
        card_body = [
            html.P("Products that most frequently changed from 'In Stock' to 'Out of Stock' between scrapes.", className="card-text text-muted small"),
            dbc.Table(table_header + table_body, bordered=True, hover=True, striped=True, responsive=True)
        ]

    # Mode 2: Not enough history, show what's out of stock right now
    else:
        card_header = "⚠️ Immediate Attention: Currently Out of Stock"
        out_of_stock_df = latest_products_df[latest_products_df['stock_status'] == 'Out of Stock']
        
        if out_of_stock_df.empty:
            card_body = html.Div([
                html.P("✅ All products are currently in stock.", className="text-success"),
                html.P("Historical demand data will be calculated after the next scrape.", className="text-muted small")
            ])
        else:
            table_header = [html.Thead(html.Tr([html.Th("Product"), html.Th("Category")]))]
            table_rows = []
            for row in out_of_stock_df.head(10).itertuples():
                 table_rows.append(
                    html.Tr([
                        html.Td(html.A(row.title, href=row.url, target="_blank", rel="noopener noreferrer")),
                        html.Td(row.category)
                    ])
                )
            table_body = [html.Tbody(table_rows)]
            card_body = [
                html.P("These products are unavailable in the latest data snapshot. Restock recommended.", className="card-text text-muted small"),
                dbc.Table(table_header + table_body, bordered=True, hover=True, striped=True, responsive=True)
            ]

    return dbc.Card([
        dbc.CardHeader(card_header),
        dbc.CardBody(card_body)
    ], className="mb-3")


def create_stockout_category_chart(df):
    """
    Creates a bar chart showing the percentage of out-of-stock items per category.
    This helps identify categories that need attention.
    """
    if df.empty or 'stock_status' not in df.columns or 'category' not in df.columns:
        fig = go.Figure()
        fig.add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig

    # Calculate stock-out counts per category
    stock_status_counts = df.groupby(['category', 'stock_status']).size().unstack(fill_value=0)
    
    if 'Out of Stock' not in stock_status_counts.columns:
        stock_status_counts['Out of Stock'] = 0
    if 'In Stock' not in stock_status_counts.columns:
        stock_status_counts['In Stock'] = 0

    stock_status_counts['total'] = stock_status_counts['In Stock'] + stock_status_counts['Out of Stock']
    stock_status_counts['stock_out_rate'] = (stock_status_counts['Out of Stock'] / stock_status_counts['total']) * 100
    
    # Sort by the highest stock-out rate
    stock_status_counts = stock_status_counts.sort_values(by='stock_out_rate', ascending=False).reset_index()

    fig = px.bar(
        stock_status_counts,
        x='category',
        y='stock_out_rate',
        labels={'category': 'Category', 'stock_out_rate': 'Out of Stock (%)'},
        text=stock_status_counts['stock_out_rate'].apply(lambda x: f'{x:.1f}%')
    )
    fig.update_layout(
        xaxis_title=None,
        yaxis_title="Out of Stock Rate (%)",
        uniformtext_minsize=8, 
        uniformtext_mode='hide',
        title_x=0.5,
        title_text="Stock-Out Rate by Category"
    )
    return fig

def create_price_distribution_chart(df):
    """Create a histogram for price distribution"""
    if df.empty or 'price' not in df.columns:
        fig = go.Figure()
        fig.add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig
    
    fig = px.histogram(df, x='price', nbins=20, title="Price Distribution")
    fig.update_layout(
        xaxis_title="Price (₪)",
        yaxis_title="Number of Products",
        title_x=0.5
    )
    return fig

def create_stock_history_chart(history):
    """
    Creates an adaptive chart for stock history.
    - If history has multiple data points, it shows a line chart.
    - If it has a single data point, it shows a KPI indicator.
    - If it's empty, it shows 'No data available'.
    """
    if not history:
        fig = go.Figure()
        fig.add_annotation(text="No data available for history chart.", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig

    # If there's only one record, show a KPI indicator instead of a single-point chart
    if len(history) == 1:
        total_in_stock = history[0].get('in_stock', 0)
        fig = go.Figure(go.Indicator(
            mode="number",
            value=total_in_stock,
            title={"text": "Total Items Currently In Stock"},
            domain={'y': [0, 1], 'x': [0, 1]}
        ))
        fig.update_layout(
            title_text="Current Inventory Snapshot",
            title_x=0.5
        )
        return fig

    # If we have enough data, show the line chart
    history_df = pd.DataFrame(history)
    history_df['date'] = pd.to_datetime(history_df['date'])
    
    fig = px.line(
        history_df, 
        x='date', 
        y='in_stock', 
        labels={'date': 'Date', 'in_stock': 'Number of Products In Stock'},
        markers=True
    )
    fig.update_layout(title_x=0.5, title_text='Stock Level Over Time')
    return fig


def create_stock_category_history_chart(history):
    """Chart showing stock level by category over time"""
    if not history:
        fig = go.Figure()
        fig.add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig
    
    if len(history) < 2:
        fig = go.Figure()
        fig.add_annotation(text="Not enough historical data for category trend.", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig

    history_df = pd.DataFrame(history)
    dates = pd.to_datetime(history_df['date'])
    
    traces = []
    # Get all unique categories across all history points
    all_categories = set()
    for counts in history_df['category_counts']:
        if isinstance(counts, dict):
            all_categories.update(counts.keys())
            
    for category in sorted(list(all_categories)):
        y_values = []
        for counts in history_df['category_counts']:
             y_values.append(counts.get(category, 0) if isinstance(counts, dict) else 0)
        
        traces.append(go.Scatter(x=dates, y=y_values, mode='lines+markers', name=category))

    fig = go.Figure(data=traces)
    fig.update_layout(
        title="Stock Level by Category Over Time", 
        xaxis_title="Date", 
        yaxis_title="Number of Products In Stock",
        title_x=0.5
    )
    return fig
    
def create_database_status_card(df):
    """Creates a card with database status based on the DataFrame"""
    if df.empty or 'error' in df.columns:
        status_text = "Error"
        status_color = "danger"
        if not df.empty and 'error' in df.columns:
            error_message = df['error'].iloc[0]
            status_children = [
                html.H5("Database Status", className="card-title"),
                html.P(f"Status: {status_text}", className=f"card-text text-{status_color}"),
                html.P(f"Details: {error_message}", className="card-text text-muted small")
            ]
        else:
             status_children = [
                html.H5("Database Status", className="card-title"),
                html.P(f"Status: {status_text}", className=f"card-text text-{status_color}"),
                html.P("Could not load data. Check logs.", className="card-text text-muted small")
            ]
    else:
        status_text = "Connected"
        status_color = "success"
        total_products = len(df)
        status_children = [
            html.H5("Database Status", className="card-title"),
            html.P(f"Status: {status_text}", className=f"card-text text-{status_color}"),
            html.P(f"Loaded Products: {total_products}", className="card-text text-muted small")
        ]

    return dbc.Card(dbc.CardBody(status_children), className="h-100")

def create_scraping_status_card(latest_session):
    """Creates a card displaying the status of the latest scraping session"""
    if not latest_session or 'error' in latest_session:
        status_text = "Error"
        status_color = "danger"
        if latest_session and 'error' in latest_session:
            details = latest_session.get('error', 'Unknown error')
        else:
            details = "Could not load session data."
        
        status_children = [
            html.H5("Last Scraper Run", className="card-title"),
            html.P(f"Status: {status_text}", className=f"card-text text-{status_color}"),
            html.P(f"Details: {details}", className="card-text text-muted small")
        ]
    else:
        status_text = latest_session.get('status', 'N/A')
        # Make the check case-insensitive to handle 'completed', 'Completed', etc.
        status_color = "success" if status_text.lower() == "completed" else "warning"
        
        start_time_utc = latest_session.get('session_start')
        if start_time_utc:
            # Convert to pandas Timestamp
            ts = pd.to_datetime(start_time_utc)
            # If the timestamp from the DB is naive (no timezone), 
            # assume it's UTC and make it timezone-aware.
            if ts.tzinfo is None:
                ts = ts.tz_localize('UTC')
            
            # Now it's safe to convert to the server's local timezone for display.
            # tz_convert(None) converts to local and removes tzinfo for clean formatting.
            start_time_local = ts.tz_convert(None)
            start_time_str = start_time_local.strftime('%Y-%m-%d %H:%M:%S')
        else:
            start_time_str = "N/A"
            
        duration = latest_session.get('duration_seconds')
        if duration is not None:
            duration_str = f"{duration:.2f} sec"
        else:
            duration_str = "N/A"

        status_children = [
            html.H5("Last Scraper Run", className="card-title"),
            html.P(f"Status: {status_text}", className=f"card-text text-{status_color}"),
            html.P(f"Started: {start_time_str}", className="card-text text-muted small"),
            html.P(f"Duration: {duration_str}", className="card-text text-muted small")
        ]
        
    return dbc.Card(dbc.CardBody(status_children), className="h-100")

def create_kpi_cards(df):
    """Creates a row of KPI cards for the main dashboard."""
    if df.empty:
        # Return placeholder cards if there's no data
        kpi_row = dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody("-"), color="light"), md=4),
            dbc.Col(dbc.Card(dbc.CardBody("-"), color="light"), md=4),
            dbc.Col(dbc.Card(dbc.CardBody("-"), color="light"), md=4),
        ])
        return kpi_row

    total_products = len(df)
    in_stock_count = len(df[df['stock_status'] == 'In Stock'])
    out_of_stock_count = total_products - in_stock_count
    stock_out_rate = (out_of_stock_count / total_products) * 100 if total_products > 0 else 0
    
    # Define color thresholds for stock-out rate
    if stock_out_rate > 25:
        rate_color = "danger"
    elif stock_out_rate > 10:
        rate_color = "warning"
    else:
        rate_color = "success"

    kpi_cards = [
        dbc.Col(dbc.Card([
            dbc.CardHeader("Total Items In Stock"),
            dbc.CardBody([
                html.H4(f"{in_stock_count}", className="card-title")
            ])
        ]), md=4, className="mb-3"),
        
        dbc.Col(dbc.Card([
            dbc.CardHeader("Overall Stock-Out Rate"),
            dbc.CardBody([
                html.H4(f"{stock_out_rate:.1f}%", className=f"card-title text-{rate_color}")
            ])
        ]), md=4, className="mb-3"),

        dbc.Col(dbc.Card([
            dbc.CardHeader("Tracked Categories"),
            dbc.CardBody([
                html.H4(f"{df['category'].nunique()}", className="card-title")
            ])
        ]), md=4, className="mb-3"),
    ]

    return dbc.Row(kpi_cards)

# --- Layout ---
app.layout = dbc.Container(
    [
        html.H1("Agilite Sales Intelligence", className="my-4 text-center"),
        
        dcc.Interval(
            id='interval-component',
            interval=5*60*1000,  # in milliseconds (5 minutes)
            n_intervals=0
        ),
        
        # Row for KPI cards
        html.Div(id='kpi-card-row'),

        # Row for status cards
        dbc.Row(
            [
                dbc.Col(html.Div(id='db-status-card'), width=12, md=6, className="mb-3"),
                dbc.Col(html.Div(id='scraping-status-card'), width=12, md=6, className="mb-3"),
            ],
        ),
        
        html.Hr(),
        
        # Row for the main adaptive card (High-Demand or Out-of-Stock)
        dbc.Row(
            [
                dbc.Col(html.Div(id='high-demand-card'), width=12),
            ],
            className="mb-3"
        ),
        
        html.Hr(),

        # Row for historical charts
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H3("Stock Level Over Time", className="text-center"),
                        dcc.Graph(id='stock-history-chart')
                    ],
                    width=12,
                    md=6,
                    className="mb-3"
                ),
                dbc.Col(
                    [
                        html.H3("Stock by Category Over Time", className="text-center"),
                        dcc.Graph(id='stock-category-history-chart')
                    ],
                    width=12,
                    md=6,
                    className="mb-3"
                ),
            ]
        ),

        # Row for distribution charts
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H3("Price Distribution", className="text-center"),
                        dcc.Graph(id='price-distribution-chart')
                    ],
                    width=12,
                    md=6,
                    className="mb-3"
                ),
                dbc.Col(
                    [
                        html.H3("Stock-Out Rate by Category", className="text-center"),
                        dcc.Graph(id='stockout-category-chart')
                    ],
                    width=12,
                    md=6,
                    className="mb-3"
                )
            ]
        ),
        
        html.Hr()
    ],
    fluid=True
)

# --- Callback ---
@app.callback(
    [Output('kpi-card-row', 'children'),
     Output('db-status-card', 'children'),
     Output('scraping-status-card', 'children'),
     Output('stock-history-chart', 'figure'),
     Output('stock-category-history-chart', 'figure'),
     Output('price-distribution-chart', 'figure'),
     Output('high-demand-card', 'children'),
     Output('stockout-category-chart', 'figure')],
    [Input('interval-component', 'n_intervals')]
)
def update_dashboard(n):
    # Establish connection at the start of the update
    db_manager.connect()
    
    df = load_latest_data()
    history = process_stock_history()
    changelog_df = db_manager.get_product_changelog()
    high_demand_df = calculate_high_demand_products(changelog_df)

    kpi_cards = create_kpi_cards(df)
    db_status_card = create_database_status_card(df)
    latest_session = db_manager.get_latest_scraping_session()
    scraping_status_card = create_scraping_status_card(latest_session)
    high_demand_card = create_high_demand_card(high_demand_df, df)
    
    # Generate figures
    stock_history_fig = create_stock_history_chart(history)
    stock_category_history_fig = create_stock_category_history_chart(history)
    price_dist_fig = create_price_distribution_chart(df)
    stockout_category_fig = create_stockout_category_chart(df)

    # Close the connection after all data is fetched
    db_manager.disconnect()
    
    return (kpi_cards, db_status_card, scraping_status_card, stock_history_fig, 
            stock_category_history_fig, price_dist_fig, 
            high_demand_card, stockout_category_fig)

if __name__ == '__main__':
    # Connect to DB on startup to check credentials
    if db_manager.connect():
        db_manager.disconnect()
        print("Database connection successful. Starting server...")
        app.run_server(host='0.0.0.0', port=8050, debug=True)
    else:
        print("FATAL: Could not connect to the database. Please check your configuration.")
        print(f"Using connection string: postgresql://{DB_CONFIG['user']}...@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}")
        exit(1)