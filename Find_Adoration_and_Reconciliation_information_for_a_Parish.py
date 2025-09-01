#!/usr/bin/env python
# coding: utf-8

# <a href="https://colab.research.google.com/github/tomknightatl/USCCB/blob/main/Find_Adoration_and_Reconciliation_information_for_a_Parish.ipynb" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>

# In[ ]:


# Cell 1: Import libraries
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import sqlite3
import pandas as pd
import os
from google.colab import userdata


# In[ ]:


# Cell 2: Clone GitHub repository and configure Git
import os
from google.colab import userdata

# GitHub credentials
GITHUB_REPO = 'USCCB'
GITHUB_USERNAME = userdata.get('GitHubUserforUSCCB')
GITHUB_PAT = userdata.get('GitHubPATforUSCCB')

# GitHub repository URL
REPO_URL = f"https://{GITHUB_USERNAME}:{GITHUB_PAT}@github.com/{GITHUB_USERNAME}/{GITHUB_REPO}.git"

# Check if the repository directory already exists
if not os.path.exists(GITHUB_REPO):
    # Clone the repository
    get_ipython().system('git clone {REPO_URL}')
    os.chdir(GITHUB_REPO)
else:
    print(f"Repository {GITHUB_REPO} already exists. Updating...")
    os.chdir(GITHUB_REPO)
    get_ipython().system('git pull origin main')

# Configure Git
get_ipython().system('git config --global user.email "tomk@github.leemail.me"')
get_ipython().system('git config --global user.name "tomknightatl"')


# In[ ]:


# Cell 3
def get_sitemap_urls(url):
    try:
        response = requests.get(urljoin(url, '/sitemap.xml'))
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'xml')
            return [loc.text for loc in soup.find_all('loc')]
    except:
        pass
    return []


# In[ ]:


# Cell 4
def search_for_keywords(url, keywords):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            text = soup.get_text().lower()
            return any(keyword.lower() in text for keyword in keywords)
    except:
        pass
    return False


# In[ ]:


# Cell 5
def extract_time_info(url, keyword):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            text = soup.get_text()

            # Look for patterns like "X hours per week" or "X hours per month"
            time_pattern = re.compile(r'(\d+)\s*hours?\s*per\s*(week|month)', re.IGNORECASE)
            match = time_pattern.search(text)

            if match:
                hours = int(match.group(1))
                period = match.group(2).lower()
                return f"{hours} hours per {period}"

            # If no clear pattern is found, return the paragraph containing the keyword
            paragraphs = soup.find_all('p')
            for p in paragraphs:
                if keyword.lower() in p.text.lower():
                    return p.text.strip()
    except:
        pass
    return "Information not found"


# In[ ]:


# Cell 6
def scrape_parish_data(url):
    sitemap_urls = get_sitemap_urls(url)
    all_urls = [url] + sitemap_urls

    print(f"Found {len(all_urls)} URLs on Sitemap page:")
    for sitemap_url in all_urls:
        print(f"Sitemap URL: {sitemap_url}")

        # Get all links from the sitemap page
        try:
            response = requests.get(sitemap_url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                page_links = [a['href'] for a in soup.find_all('a', href=True)]
            else:
                page_links = []
        except:
            page_links = []

        print(f"Found {len(page_links)} links on {sitemap_url}")

        reconciliation_found = False
        adoration_found = False
        reconciliation_info = ""
        adoration_info = ""
        reconciliation_page = ""
        adoration_page = ""

        for page_url in [sitemap_url] + page_links:
            print(f"Checking {page_url}...")

            if not reconciliation_found and search_for_keywords(page_url, ['Reconciliation', 'Confession']):
                reconciliation_found = True
                reconciliation_info = extract_time_info(page_url, 'Reconciliation')
                reconciliation_page = page_url
                print(f"Reconciliation information found on {page_url}")

            if not adoration_found and search_for_keywords(page_url, ['Adoration']):
                adoration_found = True
                adoration_info = extract_time_info(page_url, 'Adoration')
                adoration_page = page_url
                print(f"Adoration information found on {page_url}")

            if reconciliation_found and adoration_found:
                break

        if reconciliation_found and adoration_found:
            break

    return {
        'url': url,
        'offers_reconciliation': reconciliation_found,
        'reconciliation_info': reconciliation_info,
        'reconciliation_page': reconciliation_page,
        'offers_adoration': adoration_found,
        'adoration_info': adoration_info,
        'adoration_page': adoration_page
    }


# In[ ]:


# Cell 7
parish_urls = [
    'https://allsaintsdunwoody.org/',
#    'https://sacredheartatlanta.org/',
#    'https://cathedralctk.com/',
    'https://www.christourhopeatl.org/'
]

results = []
for url in parish_urls:
    print(f"Scraping {url}...")
    result = scrape_parish_data(url)
    result['parish_name'] = url.split('//')[1].split('.')[0]
    results.append(result)
    print(f"Completed scraping {url}")


# In[ ]:


# Cell 8
df = pd.DataFrame(results)
print(df)


# In[ ]:


# Cell 9
conn = sqlite3.connect('data.db')
df.to_sql('AdorationReconcilation', conn, if_exists='replace', index=False)
conn.close()

print("Data saved to parish_data.db")


# In[ ]:


# Cell 10
# Verify data in the database
conn = sqlite3.connect('data.db')
df_from_db = pd.read_sql_query("SELECT * FROM AdorationReconcilation", conn)
conn.close()

print(df_from_db)


# In[ ]:


# Cell 11: Commit changes and push to GitHub
# Add changes to git
get_ipython().system('git add data.db')

# Commit changes
get_ipython().system('git commit -m "Added data to data.db using Find_Adoration_and_Reconciliation_information_for_a_Parish.ipynb"')

# Push changes to GitHub
get_ipython().system('git push origin main')

