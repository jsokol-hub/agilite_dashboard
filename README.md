# Agilite Sales Intelligence Dashboard

An interactive dashboard for analyzing Agilite sales, connected to a PostgreSQL/PostGIS database.

## Features

- 📊 **KPI Cards:** At-a-glance metrics for Total Items In Stock, Overall Stock-Out Rate, and Tracked Categories.
- 🧠 **Adaptive Insights:**
    - Shows **High-Demand Products** (likely top-sellers) based on historical stock changes.
    - If history is insufficient, it automatically shows **Immediate Attention: Out of Stock** items.
- 📈 **Trend Analysis:**
    - Visualizes stock level and category trends over time.
    - Adapts to show a clear KPI for a single data point, preventing "empty" charts.
- ⚠️ **Attention Areas:** A dedicated chart for **Stock-Out Rate by Category** to identify problematic product groups.
- 💰 **Price Distribution Analysis:** A histogram showing the distribution of product prices.
- 🗄️ **Database Integration:** Connects to a PostgreSQL/PostGIS database.
- ⏰ **Auto-Refresh:** Automatically updates data every 5 minutes.
- 🚀 **Deployment-Ready:** Fully configured for one-click deployment on CapRover.

## Requirements

- Python 3.9+
- PostgreSQL 12+ with the PostGIS extension
- Docker
- CapRover (for deployment)

## Local Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd Agilite_dash
    ```

2.  **Create and configure the environment file:**
    -   Copy `env_example.txt` to `.env`.
    -   Fill in `.env` with your database connection credentials.

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the application:**
    ```bash
    python app.py
    ```
    The dashboard will be available at: http://localhost:8050

## Deployment on CapRover

This application is fully prepared for deployment on CapRover.

1.  **Prepare your Git repository:**
    -   Create a new repository on GitHub (or another service).
    -   Run `git init`, `git add .`, `git commit -m "Initial commit"`, and `git push` to upload the code.

2.  **Create a new app in CapRover:**
    -   In the CapRover interface, go to the "Apps" section and create a new app (e.g., `agilite-dashboard`).
    -   Important: **Do not enable** "Persistent Data," as the application is stateless.

3.  **Configure the deployment method:**
    -   Go to the "Deployment" tab.
    -   Select "Method 1: Official CapRover Apps".
    -   Specify your repository (e.g., `your-username/your-repo`), branch (`main` or `master`), and click "SAVE & UPDATE".

4.  **Configure environment variables:**
    -   Go to the "App Configs" tab.
    -   In the "Environment Variables" section, you **must** add all the variables required to connect to your database:
        -   `DB_HOST`
        -   `DB_PORT`
        -   `DB_NAME`
        -   `DB_USER`
        -   `DB_PASSWORD`
        -   `DB_SCHEMA` (must be `agilite`)
    -   You can also set Dash-related variables:
        -   `DASH_DEBUG=False` (recommended for production)

5.  **Enable HTTPS (Recommended):**
    -   In the "App Configs" tab, enable HTTPS. This will encrypt traffic.

6.  **Deploy the application:**
    -   CapRover will automatically start the build and deployment process after you save the deployment settings. You can click "Deploy Now" to trigger the process manually.

Once the deployment is complete, your dashboard will be available at the URL provided by CapRover.

## Project Structure

```
Agilite_dash/
├── app.py                   # Main Dash application
├── config.py                # Database configuration
├── database.py              # Module for database interaction
├── requirements.txt         # Python dependencies
├── Dockerfile               # Instructions for building the Docker container
├── captain-definition       # Configuration file for CapRover
├── .gitignore               # File to exclude artifacts from Git
├── env_example.txt          # Example environment file
└── README.md                # Documentation
```
## Database Schema

The dashboard reads from the `agilite` schema, which is expected to be populated by an external scraper. The primary table used is `agilite.products`.

### `products` Table
The application expects a table with the following columns to function correctly:
- `title` - Product name
- `price` - Price
- `url` - Link to the product
- `stock_status` - Stock availability status
- `variant_count` - Number of product variants
- `category` - Product category
- `processing_timestamp` - The timestamp when the product data was scraped. This is crucial for historical analysis.
- `session_id` - An identifier for the scraping session.

**Note:** The application logic is built around the idea that the scraper **appends** new records for each run, rather than updating existing ones. This is essential for building the historical stock level charts.

## Troubleshooting

### Database Connection Issues

1.  Verify the connection parameters in your `.env` file (for local) or in CapRover's environment variables (for production).
2.  Ensure the PostgreSQL server is running and accessible from the application.
3.  Check the database user's permissions.

### Data Display Problems

1.  Confirm that the scraper is successfully populating the `agilite.products` table.
2.  Verify that the table schema matches the expected structure.
3.  Check the application logs in CapRover for any errors during data fetching or processing.

## Development

### Adding New Charts

1.  Create a new chart generation function in `app.py`.
2.  Add a new component for the chart in the `app.layout`.
3.  Update the `update_dashboard` callback to provide data to the new chart.

### Extending Database Functionality

1.  Add new data-fetching methods to the `DatabaseManager` class in `database.py`.
2.  Create new functions in `app.py` to process the data from these new methods.

## License

MIT License 