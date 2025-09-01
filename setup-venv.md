# USCCB Project Setup Guide

This guide provides instructions on how to set up the project environment, install dependencies, and prepare the necessary API keys for running the scripts and notebooks.

## 1. Prerequisites

Ensure you have Python 3.8 or higher installed on your system.

## 2. Create and Activate a Virtual Environment

It is highly recommended to use a virtual environment to manage project dependencies.

```bash
# Navigate to the root of your project directory
cd /home/tomk/USCCB

# Create a virtual environment named 'venv'
python3 -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
# .\venv\Scripts\activate
```

Your command prompt should now show `(venv)` indicating the virtual environment is active.

## 3. Install Dependencies

With your virtual environment activated, install the required Python packages using `pip`:

```bash
pip install -r requirements.txt
```

## 4. Configure Environment Variables

This project uses environment variables to securely store API keys and other sensitive information. You need to create a `.env` file in the root directory of the project.

Create a file named `.env` in `/home/tomk/USCCB/` with the following content, replacing the placeholder values with the actual keys, which Tom has saved in the LastPass password named ".env file for USCCB repo" linked to the URL https://github.com:

```
SUPABASE_URL="your_supabase_url_here"
SUPABASE_KEY="your_supabase_anon_key_here"
GENAI_API_KEY_USCCB="your_google_genai_api_key_here"
SEARCH_API_KEY_USCCB="your_google_custom_search_api_key_here"
SEARCH_CX_USCCB="your_google_custom_search_engine_id_here"
```

**Important:**
*   **Do not commit your `.env` file to version control (e.g., Git).** It contains sensitive information. A `.gitignore` entry for `.env` is usually recommended.
*   The notebooks will be modified to read these variables using `python-dotenv`.

## 5. Running Jupyter Notebooks and Python Scripts

### Converting Notebooks to Python Scripts

To convert all Jupyter notebooks (`.ipynb`) located in the `notebooks/` directory to Python scripts (`.py`) in the root directory, ensure your virtual environment is activated, then run the following commands:

```bash
for notebook in notebooks/*.ipynb; do
  jupyter nbconvert --to script "$notebook" --output-dir . --output-extension .py
done
```
This command will iterate through all `.ipynb` files in the `notebooks/` directory and convert each one into a corresponding `.py` file in the root of your project.

### Running Python Scripts

You can run the Python scripts directly from your terminal:

```bash
python YOUR_SCRIPT_NAME.py
```

### Running Jupyter Notebooks

To run the Jupyter notebooks interactively, first ensure your virtual environment is activated, then start the Jupyter server:

```bash
jupyter notebook
```
This will open a browser window where you can navigate to and run the notebooks in the `notebooks/` directory.

## 6. Chrome Installation for Selenium

The project uses Selenium for web scraping, which requires a Chrome browser and ChromeDriver. Ensure Chrome is installed on your system. The `webdriver-manager` library will attempt to download the correct ChromeDriver automatically.

If you encounter issues with Chrome or ChromeDriver, ensure Chrome is up-to-date and check the `webdriver-manager` documentation for troubleshooting.