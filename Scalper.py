import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import SessionNotCreatedException, WebDriverException, TimeoutException
import os
from urllib.parse import urljoin
import time
import re

# --- Helper Function to find Brave ---
def get_brave_path():
    """Checks common locations for the Brave browser executable."""
    if os.name == 'nt':  # Windows
        possible_paths = [
            os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
            os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "BraveSoftware", "Brave-Browser", "Application", "brave.exe")
        ]
    elif os.name == 'posix':  # macOS or Linux
        possible_paths = [
            "/usr/bin/brave-browser",  # Linux
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"  # macOS
        ]
    else:
        return None

    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None

# --- Core Scraping Logic ---
def scrap_data(url, browser_choice):
    """
    Scrapes a website using a dual-logic approach: first trying a static parse
    of FAQ "panel" content, then falling back to a sequential scan for articles.
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36")

    if browser_choice == "Brave":
        brave_path = get_brave_path()
        if brave_path:
            chrome_options.binary_location = brave_path
        else:
            st.warning("Brave browser not found in common locations. Defaulting to Chrome.")

    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)
        
        sections = []

        # --- NEW: Logic 1 - Static parsing for FAQ panels. ---
        try:
            # Explicitly wait for the panels to be loaded on the page
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.panel.panel-default"))
            )
            # Add a small buffer for any final JS rendering
            time.sleep(2)
            
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')

            panels = soup.select('div.panel.panel-default')
            if panels:
                for panel in panels:
                    question_tag = panel.select_one('.panel-title a')
                    answer_body = panel.select_one('.panel-body')

                    if question_tag and answer_body:
                        heading = question_tag.get_text(" ", strip=True)
                        if not heading:
                            continue
                        
                        content_blocks = []
                        # Find all content tags within the answer body
                        for tag in answer_body.find_all(['p', 'ul', 'ol']):
                            if tag.name == 'p':
                                text = tag.get_text(" ", strip=True)
                                if text:
                                    links = [urljoin(url, a['href']) for a in tag.find_all('a', href=True)]
                                    content_blocks.append({
                                        "type": "paragraph",
                                        "text": text,
                                        "links": links
                                    })
                            elif tag.name in ['ul', 'ol']:
                                list_items = [li.get_text(" ", strip=True) for li in tag.find_all('li') if li.get_text(strip=True)]
                                if list_items:
                                    links = [urljoin(url, a['href']) for a in tag.find_all('a', href=True)]
                                    content_blocks.append({"type": "list", "items": list_items, "links": links})
                        
                        if content_blocks:
                            sections.append({
                                "heading": heading,
                                "content_blocks": content_blocks
                            })
                
                # If this strategy yielded results, return them and do not fall back.
                if sections:
                    return pd.DataFrame(sections)

        except TimeoutException:
            # This is not an error, it just means the page doesn't have the FAQ structure.
            # The code will now naturally fall back to the general scraper below.
            pass
        except Exception:
            # Let it fall back to the general scraper on other errors.
            pass

        # --- FALLBACK: Logic 2 - If no panels found, use sequential scan for articles ---
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        body = soup.body
        if not body: return pd.DataFrame()

        current_section = {"heading": "Introduction / Preamble", "content_blocks": []}
        def section_has_content(section): return bool(section['content_blocks'])

        for tag in body.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol', 'table', 'img']):
            if tag.name.startswith("h"):
                if section_has_content(current_section): sections.append(current_section)
                current_section = {"heading": tag.get_text(" ", strip=True), "content_blocks": []}
            elif tag.name == 'p':
                text = tag.get_text(" ", strip=True)
                if text:
                    links = [urljoin(url, a['href']) for a in tag.find_all('a', href=True)]
                    current_section["content_blocks"].append({"type": "paragraph", "text": text, "links": links})
            elif tag.name in ['ul', 'ol']:
                list_items = [li.get_text(" ", strip=True) for li in tag.find_all('li') if li.get_text(strip=True)]
                if list_items:
                    links = [urljoin(url, a['href']) for a in tag.find_all('a', href=True)]
                    current_section['content_blocks'].append({"type": "list", "items": list_items, "links": links})
            elif tag.name == 'table':
                try:
                    dfs = pd.read_html(str(tag), flavor='bs4', header=0)
                    if dfs:
                        links = [urljoin(url, a['href']) for a in tag.find_all('a', href=True)]
                        current_section['content_blocks'].append({"type": "table", "markdown": dfs[0].to_markdown(index=False), "links": links})
                except Exception: pass
            elif tag.name == 'img':
                if tag.has_attr('src'):
                    src = tag['src']
                    if src and not src.startswith('data:image'):
                        current_section['content_blocks'].append({"type": "image", "src": urljoin(url, src)})
        
        if section_has_content(current_section):
            sections.append(current_section)

        return pd.DataFrame(sections)

    except (SessionNotCreatedException, TimeoutException, WebDriverException) as e:
        error_message = str(e)
        if "session not created" in error_message:
            st.error(f"Fatal Error: Browser driver version mismatch.\n\nDetails: {getattr(e, 'msg', error_message)}")
        elif "cannot find Chrome binary" in error_message:
             st.error("Fatal Error: Selenium could not find the Chrome or Brave browser installation.")
        else:
            st.error(f"An error occurred during scraping: {e}")
        return pd.DataFrame()
    
    finally:
        if driver:
            driver.quit()

# --- Streamlit UI ---
st.set_page_config(page_title="Advanced Web Scraper", layout="wide")

st.title("🚀 Advanced Web Scraper")
st.markdown("This tool extracts text, lists, tables, images, and links from websites.")

browser_choice = st.selectbox(
    "Choose a browser for scraping:",
    ("Chrome", "Brave")
)

url = st.text_input("Enter Website URL", "https://www.mosdac.gov.in/faq-page")

if st.button("Scrape Website", type="primary"):
    if not url or not url.startswith('http'):
        st.error("Please enter a valid URL (e.g., https://example.com).")
    else:
        with st.spinner(f"Scraping {url} using {browser_choice}... This might take a moment."):
            raw_df = scrap_data(url, browser_choice)
        
        if raw_df.empty:
            st.error("Could not scrape the website. It might be heavily protected, the structure is unreadable, or there was a browser/driver issue.")
        else:
            st.success(f"Successfully scraped {len(raw_df)} content sections!")

            st.markdown(f"**Info taken from this link:** [{url}]({url})")
            
            # --- MOVED: Download section is now at the top ---
            st.subheader("📥 Download Data")
            
            def format_section_for_csv(content_blocks):
                full_text = []
                for block in content_blocks:
                    block_text = ""
                    if block['type'] == 'paragraph':
                        block_text = f"PARAGRAPH:\n{block['text']}"
                        if block['links']:
                            links_str = "\n".join(block['links'])
                            block_text += f"\n[Links:\n{links_str}]"
                    elif block['type'] == 'list':
                        items_str = "\n".join([f"- {item}" for item in block['items']])
                        block_text = f"LIST:\n{items_str}"
                        if block['links']:
                            links_str = "\n".join(block['links'])
                            block_text += f"\n[Links:\n{links_str}]"
                    elif block['type'] == 'table':
                        block_text = f"TABLE:\n{block['markdown']}"
                        if 'links' in block and block['links']:
                            links_str = "\n".join(block['links'])
                            block_text += f"\n[Links:\n{links_str}]"
                    elif block['type'] == 'image':
                        src = block['src'].replace('"', '""') 
                        block_text = f"IMAGE: =HYPERLINK(\"{src}\", \"Click to view image\")"
                    full_text.append(block_text)
                return "\n\n---\n\n".join(full_text)

            export_df = raw_df.copy()
            export_df['content'] = export_df['content_blocks'].apply(format_section_for_csv)
            export_df = export_df[['heading', 'content']]
            
            # --- MODIFIED: Generate filename from URL ---
            # Remove protocol (http, https)
            file_name_base = re.sub(r'^https?:\/\/', '', url)
            # Replace invalid filename characters with underscores
            file_name_base = re.sub(r'[\/\.:?=&]', '_', file_name_base)
            # Remove any trailing underscores
            file_name = f"{file_name_base.strip('_')}.csv"

            csv_data = export_df.to_csv(index=False)
            csv_header = f"\"Info taken from this link:\",\"{url}\"\n"
            full_csv_content = csv_header + csv_data
            csv_bytes = full_csv_content.encode('utf-8')
            
            st.download_button(
                label="Download data as CSV",
                data=csv_bytes,
                file_name=file_name,
                mime="text/csv",
            )

            st.markdown("---") 

            # --- Scraped content is now displayed below the download button ---
            st.subheader("📄 Scraped Content")
            for _, row in raw_df.iterrows():
                summary = []
                num_paras = sum(1 for b in row['content_blocks'] if b['type'] == 'paragraph')
                num_lists = sum(1 for b in row['content_blocks'] if b['type'] == 'list')
                num_tables = sum(1 for b in row['content_blocks'] if b['type'] == 'table')
                num_images = sum(1 for b in row['content_blocks'] if b['type'] == 'image')
                all_links = []
                for b in row['content_blocks']:
                    if 'links' in b:
                        all_links.extend(b['links'])

                if num_paras > 0: summary.append(f"{num_paras} paragraphs")
                if len(all_links) > 0: summary.append(f"{len(set(all_links))} links")
                if num_lists > 0: summary.append(f"{num_lists} lists")
                if num_tables > 0: summary.append(f"{num_tables} tables")
                if num_images > 0: summary.append(f"{num_images} images")

                expander_title = f"**{row['heading']}** ({', '.join(summary)})" if summary else f"**{row['heading']}**"
                
                with st.expander(expander_title, expanded=True): # Expanded by default for FAQs
                    for block in row['content_blocks']:
                        if block['type'] == 'paragraph':
                            st.markdown(f"> {block['text']}")
                            if block['links']:
                                st.markdown("**Links in this paragraph:**")
                                for link in block['links']:
                                    st.markdown(f"- {link}")
                            st.markdown("---")
                        
                        elif block['type'] == 'list':
                            st.markdown("#### List")
                            st.markdown("\n".join([f"- {item}" for item in block['items']]))
                            if block['links']:
                                st.markdown("**Links in this list:**")
                                for link in block['links']:
                                    st.markdown(f"- {link}")
                            st.markdown("---")

                        elif block['type'] == 'table':
                            st.markdown("#### Table")
                            st.markdown(block['markdown'], unsafe_allow_html=True)
                            if 'links' in block and block['links']:
                                st.markdown("**Links in this table:**")
                                for link in block['links']:
                                    st.markdown(f"- {link}")
                            st.markdown("---")

                        elif block['type'] == 'image':
                            st.markdown("#### Image")
                            try:
                                st.image(block['src'], width=300)
                            except Exception:
                                st.warning(f"Could not load image: {block['src']}")
                            st.markdown("---")

