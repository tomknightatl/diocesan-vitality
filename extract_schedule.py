#!/usr/bin/env python
# coding: utf-8

# <a href="https://colab.research.google.com/github/tomknightatl/USCCB/blob/main/Find_Adoration_and_Reconciliation_information_for_a_Parish.ipynb" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>

# In[ ]:


# Cell 1: Import libraries
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import os
from datetime import datetime, timezone
import argparse # Added
from dotenv import load_dotenv # Added
from supabase import create_client, Client # Added
import config
from core.logger import get_logger

logger = get_logger(__name__)


# In[ ]:


def main(num_parishes=config.DEFAULT_NUM_PARISHES_FOR_SCHEDULE):
    # Cell 2: Command-line arguments and Supabase setup
    load_dotenv() # Load environment variables from .env file

    # Initialize Supabase client
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    supabase: Client = create_client(supabase_url, supabase_key)

    # In[ ]:


    # Cell 3: (Original Cell 2 content, modified to remove Colab-specific git commands)
    # This section is for setting up the environment, not directly related to the core scraping logic.
    # Assuming the repository is already cloned and configured in a standard environment.
    # Removed Colab-specific git clone and config commands.
    # If running in a non-Colab environment, ensure your working directory is the project root.
    # GitHub credentials are now handled via environment variables if needed elsewhere.
    # GITHUB_REPO = 'USCCB'
    # GITHUB_USERNAME = os.getenv('GitHubUserforUSCCB') # Using os.getenv instead of userdata
    # GITHUB_PAT = os.getenv('GitHubPATforUSCCB') # Using os.getenv instead of userdata

    # REPO_URL = f"https://{GITHUB_USERNAME}:{GITHUB_PAT}@github.com/{GITHUB_USERNAME}/{GITHUB_REPO}.git"

    # # Check if the repository directory already exists
    # if not os.path.exists(GITHUB_REPO):
    #     # Clone the repository
    #     # subprocess.run(['git', 'clone', REPO_URL]) # Use subprocess.run for standalone scripts
    #     # os.chdir(GITHUB_REPO)
    #     logger.info("Repository not found. Please ensure you are running from the project root or clone manually.")
    # else:
    #     # os.chdir(GITHUB_REPO)
    #     # subprocess.run(['git', 'pull', 'origin', 'main']) # Use subprocess.run for standalone scripts
    #     logger.info(f"Repository {GITHUB_REPO} already exists. Assuming it's up to date.")

    # # Configure Git (if needed for commits from this script)
    # # subprocess.run(['git', 'config', '--global', 'user.email', 'tomk@github.leemail.me'])
    # # subprocess.run(['git', 'config', '--global', 'user.name', 'tomknightatl'])


    # In[ ]:


    # Cell 3
    def get_sitemap_urls(url):
        try:
            response = requests.get(urljoin(url, '/sitemap.xml'))
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'xml')
                urls = []
                for loc in soup.find_all('loc'):
                    if loc.text and loc.text.startswith(('http://', 'https://')) and 'default' not in loc.text:
                        urls.append(loc.text)
                return urls
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
        visited_urls = set()

        logger.info(f"Found {len(all_urls)} URLs on Sitemap page:")
        for sitemap_url in all_urls:
            logger.info(f"Sitemap URL: {sitemap_url}")

            # Get all links from the sitemap page
            try:
                response = requests.get(sitemap_url)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    page_links = [urljoin(sitemap_url, a['href']) for a in soup.find_all('a', href=True)]
                else:
                    page_links = []
            except:
                page_links = []

            logger.info(f"Found {len(page_links)} links on {sitemap_url}")

            reconciliation_found = False
            adoration_found = False
            reconciliation_info = ""
            adoration_info = ""
            reconciliation_page = ""
            adoration_page = ""

            for page_url in [sitemap_url] + page_links:
                if page_url in visited_urls:
                    continue
                visited_urls.add(page_url)

                if not page_url.startswith(('http://', 'https://')):
                    continue

                # Ignore links to files
                if re.search(r'\.(pdf|jpg|jpeg|png|gif|svg|zip|docx|xlsx|pptx|mp3|mp4|avi|mov)$', page_url, re.IGNORECASE):
                    continue

                logger.debug(f"Checking {page_url}...")

                if not reconciliation_found and search_for_keywords(page_url, ['Reconciliation', 'Confession']):
                    reconciliation_found = True
                    reconciliation_info = extract_time_info(page_url, 'Reconciliation')
                    reconciliation_page = page_url
                    logger.info(f"Reconciliation information found on {page_url}")

                if not adoration_found and search_for_keywords(page_url, ['Adoration']):
                    adoration_found = True
                    adoration_info = extract_time_info(page_url, 'Adoration')
                    adoration_page = page_url
                    logger.info(f"Adoration information found on {page_url}")

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
            'adoration_page': adoration_page,
            'scraped_at': datetime.now(timezone.utc).isoformat()
        }


    # In[ ]:


    # Cell 7: Fetch parish URLs from Supabase and process
    parish_urls = []
    try:
        # Fetch all parishes with a valid URL
        all_parishes_response = supabase.table('Parishes').select('Web').not_.is_('Web', 'null').execute()
        all_parish_urls = {p['Web'] for p in all_parishes_response.data if p['Web']}
        logger.info(f"Found {len(all_parish_urls)} parishes with websites in the 'Parishes' table.")

        # Fetch all parishes that already have a schedule, ordered by oldest first
        schedules_response = supabase.table('ParishSchedules').select('url, scraped_at').order('scraped_at').execute()
        parishes_with_schedules = {item['url'] for item in schedules_response.data}
        sorted_schedules = [item['url'] for item in schedules_response.data]
        logger.info(f"Found {len(parishes_with_schedules)} parishes in the 'ParishSchedules' table.")

        # Prioritize parishes that are not yet in ParishSchedules
        parishes_to_scrape_new = [url for url in all_parish_urls if url not in parishes_with_schedules]
        logger.info(f"Found {len(parishes_to_scrape_new)} new parishes to scrape.")

        # Add parishes to rescrape, oldest first
        parishes_to_rescrape = [url for url in sorted_schedules if url in all_parish_urls]
        
        # Combine the lists
        prioritized_urls = parishes_to_scrape_new + parishes_to_rescrape

        # Limit the number of parishes to process
        if num_parishes != 0:
            parish_urls = prioritized_urls[:num_parishes]
        else:
            parish_urls = prioritized_urls

        logger.info(f"Processing {len(parish_urls)} parishes based on priority.")

    except Exception as e:
        logger.error(f"Error fetching and prioritizing parish URLs from Supabase: {e}")

    results = []
    for url in parish_urls:
        logger.info(f"Scraping {url}...")
        result = scrape_parish_data(url)
        # Extract parish name from URL, handle cases where it might not be clean
        try:
            parish_name = url.split('//')[1].split('.')[0]
        except IndexError:
            parish_name = url # Fallback to full URL if name extraction fails
        result['parish_name'] = parish_name
        results.append(result)
        logger.info(f"Completed scraping {url}")


    # In[ ]:


    # Cell 9: Save extracted data to Supabase

    # Prepare data for Supabase upsert
    # The 'results' list already contains dictionaries with the necessary data.
    # We'll use these directly.

    if results:
        try:
            # Supabase upsert will create the table if it doesn't exist
            # and infer the schema from the first upserted object.
            # It's good practice to have a primary key for upsert to work correctly.
            # Assuming 'url' can act as a unique identifier for each parish schedule.
            response = supabase.table('ParishSchedules').upsert(results, on_conflict='url').execute()

            if hasattr(response, 'error') and response.error:
                logger.error(f"Error saving data to Supabase: {response.error}")
            else:
                logger.info(f"Successfully saved {len(results)} records to Supabase table 'ParishSchedules'.")
                # Optional: Verify data by fetching from Supabase
                # logger.info("Verifying data in Supabase...")
                # verify_response = supabase.table('ParishSchedules').select('*').limit(5).execute()
                # logger.info(verify_response.data)

        except Exception as e:
            logger.error(f"An unexpected error occurred during Supabase upsert: {e}")
    else:
        logger.info("No results to save to Supabase.")


    # In[ ]:


    # Cell 10: (Removed SQLite verification, now handled by Supabase upsert and optional verification)
    # This cell previously verified data in the local SQLite database.
    # With data now being saved to Supabase, verification would involve querying Supabase.
    # The optional verification code is commented out in Cell 9.


    # In[ ]:


    # Cell 11: Git operations (removed for standalone script compatibility)
    # Git operations are typically handled outside the script in a production environment.
    # If you need to commit and push, please do so manually from your terminal.
    # For example:
    # git add data.db
    # git commit -m "Updated adoration and reconciliation data"
    # git push origin main

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Extract adoration and reconciliation schedules from parish websites.")
    parser.add_argument(
        "--num_parishes",
        type=int,
        default=5,
        help="Maximum number of parishes to extract from. Set to 0 for no limit. Defaults to 5."
    )
    args = parser.parse_args()
    main(args.num_parishes)