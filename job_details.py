import csv
import asyncio
from playwright.async_api import async_playwright
from loguru import logger
import botright
import warnings
from bs4 import BeautifulSoup
from transformers import AutoTokenizer

# Suppress the FutureWarning for transformers
warnings.filterwarnings("ignore", category=FutureWarning, module="transformers")

# Example usage of a tokenizer (replace with your actual model name)
# Set clean_up_tokenization_spaces to True to avoid the warning
tokenizer = AutoTokenizer.from_pretrained('bert-base-uncased', clean_up_tokenization_spaces=True)

# Define log and CSV filenames
log_filename = "playwright_log.log"
input_csv_filename = "scraped_job_links.csv"  # Path to the input CSV file with job links
output_csv_filename = "scraped_job_details.csv"  # Path to the output CSV file for scraped details

# Clear the log file at the beginning
try:
    with open(log_filename, 'w'):
        pass  # Clear log file
except FileNotFoundError:
    pass

# Set up logging with loguru
logger.add(log_filename, rotation="1 week", retention="1 day", compression="zip")

# Function to read job links from input CSV file
def read_job_links():
    job_links = []
    try:
        with open(input_csv_filename, mode='r', newline='', encoding='utf-8') as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                job_links.append(row['Job Details Link'])
    except FileNotFoundError:
        logger.error(f"Input CSV file not found: {input_csv_filename}")
    return job_links

# Function to read existing links from the output CSV
def read_existing_links():
    existing_links = set()
    try:
        with open(output_csv_filename, mode='r', newline='', encoding='utf-8') as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                existing_links.add(row['Profile Link'])
    except FileNotFoundError:
        pass  # File does not exist yet, so no links to read
    return existing_links

# Function to write job data into CSV
def write_to_csv(data, existing_links):
    try:
        with open(output_csv_filename, mode='a', newline='', encoding='utf-8') as csv_file:
            fieldnames = ['Company Name','Job Title', 'Profile Link', 'Job Type', 'Salary']
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            # Write header if the file is empty
            if csv_file.tell() == 0:
                writer.writeheader()
            # Check for duplicates before writing
            if data['Profile Link'] not in existing_links:
                writer.writerow(data)
                existing_links.add(data['Profile Link'])
                logger.info(f"Appended job details to CSV: {data}")
            else:
                logger.info(f"Duplicate found: {data['Profile Link']} - Skipping entry.")
    except Exception as e:
        logger.error(f"Failed to write to CSV: {e}")

async def job_details_scraper():
    logger.info("Starting Playwright with botright proxy")

    # Read job links from input CSV
    job_links = read_job_links()

    # Load existing links to avoid duplicates
    existing_links = read_existing_links()

    # Initialize Botright asynchronously
    botright_client = await botright.Botright()

    async with async_playwright() as p:
        # Use Botright to launch Playwright browser
        browser = await botright_client.new_browser()
        page = await browser.new_page()

        # Make the browser full-screen
        await page.set_viewport_size({"width": 1920, "height": 1080})

        try:
            for job_link in job_links:
                logger.info(f"Navigating to {job_link}")
                await page.goto(job_link, timeout=60000)

                # Wait for a while to let the page fully load (adjust as needed)
                await page.wait_for_timeout(5000)  # 5 seconds delay

                # Get the page content
                page_content = await page.content()
                
                # Parse the page content with BeautifulSoup
                soup = BeautifulSoup(page_content, 'html.parser')

                job_data = {}

                try:
                    company_name = soup.select_one('.css-1ioi40n').text.strip()
                    job_data['Company Name'] = company_name
                except Exception as e:
                    logger.error(f"Failed to scrape profile_link: {e}")
                    job_data['Company Name'] = "N/A"  

                # Scrape job details
                try:
                    job_title = soup.select_one('.css-1b4cr5z').text.strip()
                    job_data['Job Title'] = job_title
                except Exception as e:
                    logger.error(f"Failed to scrape job title: {e}")  
                    job_data['Job Title'] = "N/A"

                try:
                    profile_link_element = soup.select_one('.css-1ioi40n')
                    if profile_link_element and profile_link_element.has_attr('href'):
                        profile_link = profile_link_element['href']
                        job_data['Profile Link'] = profile_link
                    else:
                        job_data['Profile Link'] = "N/A"
                        logger.info("No link found with the specified selector.")
                except Exception as e:
                    logger.error(f"Failed to scrape profile_link: {e}")
                    job_data['Profile Link'] = "N/A"

                try:
                    job_type = soup.select_one('.css-17cdm7w div').text.strip()
                    job_data['Job Type'] = job_type
                except Exception as e:
                    logger.error(f"Failed to scrape job type: {e}")
                    job_data['Job Type'] = "N/A"

                try:
                    salary = soup.select_one('#salaryInfoAndJobType .eu4oa1w0').text.strip()
                    job_data['Salary'] = salary
                except Exception as e:
                    logger.error(f"Failed to scrape salary: {e}")
                    job_data['Salary'] = "N/A"

                # Write the job data into CSV
                write_to_csv(job_data, existing_links)

        finally:
            # Close browser after scraping
            await browser.close()
            await botright_client.close()

if __name__ == "__main__":
    try:
        asyncio.run(job_details_scraper())
    except Exception as e:
        logger.error(f"Error in job details scraper: {e}")
