import csv
import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from loguru import logger
import botright
import warnings
from transformers import AutoTokenizer

# Suppress the FutureWarning for transformers
warnings.filterwarnings("ignore", category=FutureWarning, module="transformers")

# Example usage of a tokenizer (replace with your actual model name)
# Set clean_up_tokenization_spaces to True to avoid the warning
tokenizer = AutoTokenizer.from_pretrained('bert-base-uncased', clean_up_tokenization_spaces=True)

# Define log and CSV filenames
log_filename = "playwright_log.log"
csv_filename = "scraped_job_links.csv"

# Clear the log file at the beginning
try:
    with open(log_filename, 'w'):
        pass  # Clear log file
except FileNotFoundError:
    pass

# Set up logging with loguru
logger.add(log_filename, rotation="1 week", retention="1 day", compression="zip")

# Function to read existing links from CSV
def read_existing_links():
    existing_links = set()
    try:
        with open(csv_filename, mode='r', newline='', encoding='utf-8') as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                existing_links.add(row['Job Details Link'])
    except FileNotFoundError:
        pass  # File does not exist yet, so no links to read
    return existing_links

# Function to write job data into CSV
def write_to_csv(data, existing_links):
    try:
        with open(csv_filename, mode='a', newline='', encoding='utf-8') as csv_file:
            fieldnames = ['Job Title', 'Company Name', 'Job Details Link', 'Job Location', 'Job Type']
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            # Write header if the file is empty
            if csv_file.tell() == 0:
                writer.writeheader()
            # Check for duplicates before writing
            if data['Job Details Link'] not in existing_links:
                writer.writerow(data)
                existing_links.add(data['Job Details Link'])
            else:
                logger.info(f"Duplicate found: {data['Job Details Link']} - Skipping entry.")
    except Exception as e:
        logger.error(f"Failed to write to CSV: {e}")


#we are scraping each job url from listing page
async def main(pages_to_scrape):
    logger.info("Starting Playwright with botright proxy")

    # Initialize Botright asynchronously
    botright_client = await botright.Botright()

    async with async_playwright() as p:
        # Use botright to launch Playwright browser
        browser = await botright_client.new_browser()
        page = await browser.new_page()

        try:
            logger.info("Navigating to https://www.indeed.com/jobs?q=work+from+home&l=Houston%2C+TX")
            await page.goto('https://www.indeed.com/jobs?q=work+from+home&l=Houston%2C+TX', timeout=60000)
              
            # Load existing links to avoid duplicates
            existing_links = read_existing_links()

            for page_number in range(pages_to_scrape):
                logger.info(f"Processing page {page_number + 1}")

                # Get the page content
                page_content = await page.content()
                
                # Parse the page content with BeautifulSoup
                soup = BeautifulSoup(page_content, 'html.parser')

                # Find all job boxes
                job_boxes = soup.find_all('div', class_='slider_container css-12igfu2 eu4oa1w0')

                for job in job_boxes:
                    job_data = {}

                    # Scrape Job Title
                    try:
                        job_title = job.find('a', class_='jcs-JobTitle').text.strip()
                        job_data['Job Title'] = job_title
                        logger.info(f"Job Title: {job_title}")
                    except Exception as e:
                        logger.error(f"Failed to scrape job title: {e}")
                        job_data['Job Title'] = "N/A"

                    # Scrape Company Name
                    try:
                        company_name = job.find('span', {'data-testid': 'company-name'}).text.strip()
                        job_data['Company Name'] = company_name
                        logger.info(f"Company Name: {company_name}")
                    except Exception as e:
                        logger.error(f"Failed to scrape company name: {e}")
                        job_data['Company Name'] = "N/A"

                    # Scrape Job Details Link
                    try:
                        website_link = job.find('a', class_='jcs-JobTitle')['href']
                        job_data['Job Details Link'] = 'https://www.indeed.com'+website_link
                        logger.info(f"Job Details Link: {'https://www.indeed.com'+website_link}")
                    except Exception as e:
                        logger.error(f"Failed to scrape website link: {e}")
                        job_data['Job Details Link'] = "N/A"

                    # Scrape Job Location
                    try:
                        job_location = job.find('div', {'data-testid': 'text-location'}).text.strip()
                        job_data['Job Location'] = job_location
                        logger.info(f"Job Location: {job_location}")
                    except Exception as e:
                        logger.error(f"Failed to scrape job location: {e}")
                        job_data['Job Location'] = "N/A"

                    

                    # Scrape Job Type
                    try:
                        job_type = job.find('div', {'data-testid': 'attribute_snippet_testid'}).text.strip()
                        job_data['Job Type'] = job_type
                        logger.info(f"Job Type: {job_type}")
                    except Exception as e:
                        logger.error(f"Failed to scrape job type: {e}")
                        job_data['Job Type'] = "N/A"

                    # Write the job data into CSV
                    write_to_csv(job_data, existing_links)

                # Navigate to the next page using JavaScript
                if page_number < pages_to_scrape - 1:
                    try:
                        # Execute JavaScript to click on the "Next" button
                        await page.evaluate('document.querySelector("[data-testid=\'pagination-page-next\']").click()')
                        logger.info("Clicked on the next page button using JavaScript.")
                        await page.wait_for_timeout(5000)
                    except Exception as e:
                        logger.error(f"Failed to click on the next page button using JavaScript: {e}")
                        break

            logger.info("Playwright finished, closing browser.")
            await botright_client.close()

        finally:
            logger.info("Completed scraping job details.")




if __name__ == "__main__":
    try:
        pages_to_scrape = int(input("Enter the number of pages to scrape: "))
        asyncio.run(main(pages_to_scrape))
    except ValueError:
        logger.error("Invalid input. Please enter a valid number.")
