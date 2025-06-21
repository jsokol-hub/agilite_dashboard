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
    """Load the most recent data from database"""
    try:
        df = db_manager.get_latest_products()
        return df
    except Exception as e:
        print(f"Error loading data from database: {str(e)}")
        return pd.DataFrame()

def load_stock_history():
    """Load stock history from database"""
    try:
        history = db_manager.get_stock_history()
        return history
    except Exception as e:
        print(f"Error loading stock history: {str(e)}")
        return []

def create_variant_distribution_chart(df):
    """Create a pie chart showing variant distribution"""
    if df.empty or 'variant_count' not in df.columns:
        fig = go.Figure()
        fig.add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig
    
    variant_counts = df['variant_count'].value_counts()
    fig = px.pie(
        values=variant_counts.values,
        names=[f'{x} variants' for x in variant_counts.index],
        title='Product Variant Distribution'
    )
    return fig

def create_price_distribution_chart(df):
    """Create a histogram of price distribution"""
    if df.empty or 'price' not in df.columns:
        fig = go.Figure()
        fig.add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig
    
    fig = px.histogram(
        df,
        x='price',
        title='Price Distribution',
        labels={'price': 'Price (₪)'},
        nbins=20
    )
    fig.update_layout(
        xaxis_title="Price (₪)",
        yaxis_title="Number of Products"
    )
    return fig

def create_category_distribution_chart(df):
    """Create a bar chart showing category distribution"""
    if df.empty or 'category' not in df.columns:
        fig = go.Figure()
        fig.add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig
    
    category_counts = df['category'].value_counts()
    fig = px.bar(
        x=category_counts.index,
        y=category_counts.values,
        title='Product Category Distribution',
        labels={'x': 'Category', 'y': 'Number of Products'}
    )
    fig.update_layout(
        xaxis_title="Category",
        yaxis_title="Number of Products",
        xaxis_tickangle=45
    )
    return fig

def create_stock_status_chart(df):
    """Create a pie chart showing stock status distribution"""
    if df.empty or 'stock_status' not in df.columns:
        fig = go.Figure()
        fig.add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig
    
    stock_counts = df['stock_status'].value_counts()
    fig = px.pie(
        values=stock_counts.values,
        names=stock_counts.index,
        title='Product Stock Status Distribution'
    )
    return fig

def create_top_products_table(df):
    """Create a table of top products by price with links"""
    if df.empty:
        return "No data available"
    
    if 'price' not in df.columns:
        return "Price data not available"
    
    top_products = df.sort_values('price', ascending=False).head(10)
    
    # Create table with links
    table_data = []
    for _, row in top_products.iterrows():
        table_data.append({
            'Title': html.A(row['title'], href=row['url'], target='_blank') if pd.notna(row['url']) else row['title'],
            'Price': f"₪{row['price']:.2f}" if pd.notna(row['price']) else 'N/A',
            'Category': row['category'] if pd.notna(row['category']) else 'Unknown',
            'Stock Status': row['stock_status'] if pd.notna(row['stock_status']) else 'Unknown',
            'Variants': row['variant_count'] if pd.notna(row['variant_count']) else 0,
            'Images': row['image_count'] if pd.notna(row['image_count']) else 0
        })
    
    return dbc.Table.from_dataframe(
        pd.DataFrame(table_data),
        striped=True,
        bordered=True,
        hover=True
    )

def create_stock_history_chart(history):
    """Chart showing stock level over time"""
    if not history:
        fig = go.Figure()
        fig.add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig
    
    dates = [h['date'] for h in history]
    in_stock = [h['in_stock'] for h in history]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=in_stock, mode='lines+markers', name='In Stock'))
    fig.update_layout(title="Stock Level Over Time", xaxis_title="Date", yaxis_title="Number of Products In Stock")
    return fig

def create_category_stock_history_chart(history):
    """Chart showing stock by category over time"""
    if not history or not any(h['category_counts'] for h in history):
        fig = go.Figure()
        fig.add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig
    
    dates = [h['date'] for h in history]
    # Collect all categories
    all_cats = set()
    for h in history:
        if h['category_counts']:
            if isinstance(h['category_counts'], str):
                cat_counts = json.loads(h['category_counts'])
            else:
                cat_counts = h['category_counts']
            all_cats.update(cat_counts.keys())
    
    fig = go.Figure()
    for cat in sorted(all_cats):
        y = []
        for h in history:
            if h['category_counts']:
                if isinstance(h['category_counts'], str):
                    cat_counts = json.loads(h['category_counts'])
                else:
                    cat_counts = h['category_counts']
                y.append(cat_counts.get(cat, 0))
            else:
                y.append(0)
        fig.add_trace(go.Scatter(x=dates, y=y, mode='lines+markers', name=cat))
    
    fig.update_layout(title="Stock Level by Category Over Time", xaxis_title="Date", yaxis_title="Number of Products In Stock")
    return fig

def create_database_status_card(df):
    """Create a card showing database connection status and stats from the dataframe."""
    if df.empty:
        return dbc.Card([
            dbc.CardHeader("Database Status"),
            dbc.CardBody([
                html.H4("Connected", className="text-success"),
                html.P("No product data available for the last session.")
            ])
        ])

    total_products = len(df)
    in_stock_count = len(df[df['stock_status'] == 'In Stock'])
    avg_price = df['price'].mean()

    return dbc.Card([
        dbc.CardHeader("Database Status"),
        dbc.CardBody([
            html.H4("Connected", className="text-success"),
            html.P(f"Total Products: {total_products}"),
            html.P(f"In Stock: {in_stock_count}"),
            html.P(f"Average Price: ₪{avg_price:.2f}")
        ])
    ])

def create_scraping_status_card(session):
    """Create a card showing the status of the latest scraping session."""
    if not session:
        return dbc.Card([
            dbc.CardHeader("Scraping Status"),
            dbc.CardBody([
                html.H4("No Session Data", className="text-warning"),
                html.P("Could not find any scraping session records.")
            ])
        ])
    
    status_color = {
        "completed": "success",
        "running": "primary",
        "failed": "danger"
    }.get(session.get('status', 'failed').lower(), "secondary")

    end_time = session.get('session_end')
    if end_time:
        duration = end_time - session.get('session_start', end_time)
        duration_str = str(duration).split('.')[0] # Format as H:M:S
    else:
        duration_str = "Still running..."

    return dbc.Card([
        dbc.CardHeader("Latest Scraping Session Status"),
        dbc.CardBody([
            html.H4(session.get('status', 'Unknown').capitalize(), className=f"text-{status_color}"),
            html.P(f"Started: {session.get('session_start', 'N/A')}"),
            html.P(f"Duration: {duration_str}"),
            html.P(f"Products Scraped: {session.get('products_scraped', 0)}"),
            html.P(f"Products Processed: {session.get('products_processed', 0)}"),
        ]),
        dbc.CardFooter(f"Error: {session['error_message']}" if session.get('error_message') else "No errors reported.")
    ])

# Define the layout
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col(html.H1("Agilite Sales Intelligence Dashboard", className="text-center my-4"), width=12)
    ]),
    
    # Status row
    dbc.Row([
        dbc.Col(id='database-status-card', width=6, className="mb-4"),
        dbc.Col(id='scraping-status-card', width=6, className="mb-4"),
    ], className="mb-4"),
    
    dbc.Row([
        dbc.Col([
            html.H3("Category Distribution"),
            dcc.Graph(id='category-distribution-chart')
        ], width=6),
        
        dbc.Col([
            html.H3("Stock Status Distribution"),
            dcc.Graph(id='stock-status-chart')
        ], width=6)
    ]),
    
    dbc.Row([
        dbc.Col([
            html.H3("Variant Distribution"),
            dcc.Graph(id='variant-distribution-chart')
        ], width=6),
        
        dbc.Col([
            html.H3("Price Distribution"),
            dcc.Graph(id='price-distribution-chart')
        ], width=6)
    ]),
    
    dbc.Row([
        dbc.Col([
            html.H3("Top Products by Price"),
            html.Div(id='top-products-table')
        ], width=12)
    ]),

    dbc.Row([
        dbc.Col([
            html.H3("Stock Level Over Time"),
            dcc.Graph(id='stock-history-chart')
        ], width=6),
        dbc.Col([
            html.H3("Stock by Category Over Time"),
            dcc.Graph(id='category-stock-history-chart')
        ], width=6)
    ]),
    
    dcc.Interval(
        id='interval-component',
        interval=5*60*1000,  # Update every 5 minutes
        n_intervals=0
    )
])

@app.callback(
    [Output('variant-distribution-chart', 'figure'),
     Output('price-distribution-chart', 'figure'),
     Output('category-distribution-chart', 'figure'),
     Output('stock-status-chart', 'figure'),
     Output('top-products-table', 'children'),
     Output('stock-history-chart', 'figure'),
     Output('category-stock-history-chart', 'figure'),
     Output('database-status-card', 'children'),
     Output('scraping-status-card', 'children')],
    [Input('interval-component', 'n_intervals')]
)
def update_dashboard(n):
    # Establish connection at the start of the update
    db_manager.connect()
    
    df = load_latest_data()
    history = load_stock_history()
    db_status_card = create_database_status_card(df)
    latest_session = db_manager.get_latest_scraping_session()
    scraping_status_card = create_scraping_status_card(latest_session)

    # Create empty figures for when data is not available
    empty_fig = go.Figure()
    empty_fig.add_annotation(
        text="No data available",
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False
    )
    
    if df.empty:
        db_manager.disconnect() # Disconnect if no data
        return empty_fig, empty_fig, empty_fig, empty_fig, "No data available", empty_fig, empty_fig, db_status_card, scraping_status_card
    
    try:
        variant_chart = create_variant_distribution_chart(df)
        price_chart = create_price_distribution_chart(df)
        category_chart = create_category_distribution_chart(df)
        stock_chart = create_stock_status_chart(df)
        top_products = create_top_products_table(df)
        stock_history_chart = create_stock_history_chart(history)
        category_stock_history_chart = create_category_stock_history_chart(history)
        
        db_manager.disconnect() # Disconnect after successful update
        return variant_chart, price_chart, category_chart, stock_chart, top_products, stock_history_chart, category_stock_history_chart, db_status_card, scraping_status_card
    except Exception as e:
        print(f"Error updating dashboard: {str(e)}")
        db_manager.disconnect() # Disconnect on error
        return empty_fig, empty_fig, empty_fig, empty_fig, f"Error updating dashboard: {str(e)}", empty_fig, empty_fig, db_status_card, scraping_status_card

if __name__ == '__main__':
    # Initial connection test
    db_manager.connect()
    db_manager.disconnect()
    
    # Get configuration from environment
    debug = os.getenv('DASH_DEBUG', 'True').lower() == 'true'
    host = os.getenv('DASH_HOST', '0.0.0.0')
    port = int(os.getenv('DASH_PORT', 8050))
    
    app.run_server(debug=debug, host=host, port=port) 