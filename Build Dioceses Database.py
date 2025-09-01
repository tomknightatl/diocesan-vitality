#!/usr/bin/env python
# coding: utf-8

from dotenv import load_dotenv
load_dotenv()
import os

# <a href="https://colab.research.google.com/github/tomknightatl/USCCB/blob/main/Build%20Dioceses%20Database.ipynb" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>

# In[ ]:


get_ipython().system('pip install supabase')


# In[ ]:


# Cell for Supabase client initialization using Google Colab secrets
from supabase import create_client, Client
from google.colab import userdata

# Access secrets from Google Colab's userdata
try:
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')

    # Initialize Supabase client
    supabase: Client = create_client(supabase_url, supabase_key)
    print("✅ Successfully initialized Supabase client using Colab secrets.")

    # Optional: Test the connection with a simple query
    # Uncomment the lines below if you want to test the connection
    # try:
    #     result = supabase.table('your_table_name').select('*').limit(1).execute()
    #     print("✅ Connection test successful!")
    # except Exception as test_error:
    #     print(f"⚠️  Connection test failed: {test_error}")

except Exception as e:
    print(f"❌ Error accessing Colab secrets or initializing Supabase client: {e}")
    print("\n📝 To fix this:")
    print("1. Click the 🔑 key icon in the left sidebar of Colab")
    print("2. Add a new secret with name: SUPABASE_URL")
    print("3. Add another secret with name: SUPABASE_KEY")
    print("4. Make sure to enable notebook access for both secrets")
    print("5. Re-run this cell")

    # Set supabase to None so other code can check if initialization was successful
    supabase = None


# In[ ]:


# Cell 1: Import necessary libraries

import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import re
from urllib.parse import urljoin, urlparse
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraping.log"),
        logging.StreamHandler()
    ]
)


# In[ ]:


# Cell 3: Define helper functions

def get_soup(url, retries=3, backoff_factor=1.0):
    """
    Fetches the content at the given URL and returns a BeautifulSoup object.
    Implements retries with exponential backoff in case of request failures.
    """
    headers = {
        'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/58.0.3029.110 Safari/537.3'),
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive'
    }

    for attempt in range(1, retries + 1):
        try:
            logging.info(f"Attempt {attempt}: Fetching URL: {url}")
            response = requests.get(url, headers=headers, timeout=20)
            logging.info(f"Received status code: {response.status_code}")
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except requests.RequestException as e:
            logging.warning(f"Attempt {attempt} failed with error: {e}")
            if attempt == retries:
                logging.error(f"All {retries} attempts failed for URL: {url}")
                return None
            sleep_time = backoff_factor * (2 ** (attempt - 1))
            logging.info(f"Retrying in {sleep_time} seconds...")
            time.sleep(sleep_time)

def extract_dioceses(soup):
    """
    Extracts dioceses information from the parsed HTML.
    Returns a list of dictionaries with diocese details.
    """
    dioceses = []
    diocese_containers = soup.find_all('div', class_='views-row')

    logging.info(f"Found {len(diocese_containers)} potential diocese containers")

    for i, container in enumerate(diocese_containers):
        logging.info(f"Processing container {i+1}")

        da_wrap = container.find('div', class_='da-wrap')
        if not da_wrap:
            logging.warning(f"No da-wrap found in container {i+1}")
            continue

        name_div = da_wrap.find('div', class_='da-title')
        diocese_name = name_div.get_text(strip=True) if name_div else "N/A"
        logging.info(f"Diocese name: {diocese_name}")

        address_div = da_wrap.find('div', class_='da-address')
        address_parts = []
        if address_div:
            for div in address_div.find_all('div', recursive=False):
                text = div.get_text(strip=True)
                if text:
                    address_parts.append(text)

        address = ", ".join(address_parts)
        logging.info(f"Address: {address}")

        website_div = da_wrap.find('div', class_='site')
        website_url = website_div.find('a')['href'] if website_div and website_div.find('a') else "N/A"
        logging.info(f"Website: {website_url}")

        dioceses.append({
            'Name': diocese_name,
            'Address': address,
            'Website': website_url
        })

    return dioceses


# In[ ]:


# Cell 4: Fetch and parse the HTML content from URL

url = "https://www.usccb.org/about/bishops-and-dioceses/all-dioceses"
soup = get_soup(url)

if soup:
    print("Successfully fetched and parsed the dioceses page.")
    # Print the first 1000 characters of the HTML to check its structure
    print("First 1000 characters of the HTML:")
    print(soup.prettify()[:1000])
else:
    print("Failed to fetch the dioceses page. Please check your connection or the URL.")
    exit()


# In[ ]:


# Cell 5: Extract dioceses information

dioceses = extract_dioceses(soup)
print(f"Extracted information for {len(dioceses)} dioceses.")

if len(dioceses) == 0:
    print("No dioceses were extracted. Printing the structure of the page:")
    print(soup.prettify())


# In[ ]:


# Cell 6: Create a DataFrame and display results

dioceses_df = pd.DataFrame(dioceses)
print(dioceses_df.head())


# In[ ]:


# Debug your DataFrame first
print("DataFrame info:")
print("Columns:", dioceses_df.columns.tolist())
print("Shape:", dioceses_df.shape)
print("Data types:")
print(dioceses_df.dtypes)
print("\nFirst few rows:")
print(dioceses_df.head())

# Convert DataFrame to list of dictionaries (correct format for Supabase)
try:
    # Method 1: Insert all rows at once (recommended for smaller datasets)
    data_to_insert = dioceses_df.to_dict('records')  # Convert DataFrame to list of dicts

    print(f"\nAttempting to insert {len(data_to_insert)} rows...")
    print("Sample record:", data_to_insert[0] if data_to_insert else "No data")

    # Insert all data at once
    result = supabase.table('Dioceses').insert(data_to_insert).execute()

    if result.data:
        print(f"✅ Successfully inserted {len(result.data)} rows!")
    else:
        print("❌ Insert returned no data")

except Exception as e:
    print(f"❌ Bulk insert failed: {e}")
    print("\nTrying row-by-row insert for better error details...")

