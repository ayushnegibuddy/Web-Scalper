import requests
from bs4 import BeautifulSoup
import pandas as pd
import streamlit as st
from urllib.parse import urljoin
import matplotlib.pyplot as plt

def scrape_wiki_content(url):
    """Scrapes the given Wikipedia URL and extracts headings, paragraphs, and links."""
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    base_url = "{0.scheme}://{0.netloc}".format(requests.utils.urlparse(url))
    content = soup.find('div', id='bodyContent') or soup

    sections = []
    current = {"heading": "No Heading", "paragraphs": [], "links": []}

    for tag in content.find_all(['h2', 'h3', 'p']):
        if tag.name in ['h2', 'h3']:
            if current['paragraphs']:
                sections.append(current)
            current = {
                "heading": tag.get_text(" ", strip=True),
                "paragraphs": [],
                "links": []
            }

        elif tag.name == 'p':
            for sup in tag.find_all('sup'):
                sup.decompose() 

            text = tag.get_text(" ", strip=True)
            if text:
                current["paragraphs"].append(text)

                for a in tag.find_all('a', href=True):
                    href = a['href']
                    if href.startswith('/wiki/'):
                        current["links"].append(urljoin(base_url, href))

    if current['paragraphs']:
        sections.append(current)

    return pd.DataFrame(sections)

def plot_content_distribution(df):
    """Plots a graph showing the distribution of paragraphs and links for each heading."""
    df['num_paragraphs'] = df['paragraphs'].apply(len)
    df['num_links'] = df['links'].apply(len)

    fig, ax = plt.subplots(figsize=(10, 6))
    width = 0.35
    headings = df['heading']
    paragraphs = df['num_paragraphs']
    links = df['num_links']

    ax.barh(headings, paragraphs, width, label='Paragraphs')
    ax.barh(headings, links, width, left=paragraphs, label='Links', color='orange')

    ax.set_xlabel('Content Count')
    ax.set_title('Content Distribution Under Each Heading')
    ax.legend()

    plt.tight_layout()
    st.pyplot(fig)

st.set_page_config(page_title="Simple Web Scraper", layout="wide")
st.title("Simple Web Scraper")

url = st.text_input("Wikipedia URL", "https://en.wikipedia.org/wiki/World_War_II")

if st.button("Scrape"):
    try:
        if not url:
            st.error("Please provide a valid URL.")
        else:
            df = scrape_wiki_content(url)

            if df.empty:
                st.error("No content found on the page.")
            else:
                df['num_paragraphs'] = df['paragraphs'].apply(len)
                df['num_links'] = df['links'].apply(len)
                
                st.success(f"Scraped {len(df)} sections.")
                
                for index, row in df.iterrows():
                    with st.expander(row["heading"]):
                        for paragraph in row["paragraphs"]:
                            st.markdown(paragraph)
                        for link in set(row["links"]):
                            st.markdown(f"- [{link}]({link})")

                plot_content_distribution(df)

                export_df = df.copy()
                export_df['paragraphs'] = export_df['paragraphs'].apply(lambda x: "\n".join(x))
                export_df['links'] = export_df['links'].apply(lambda x: ", ".join(set(x)))
                csv = export_df.to_csv(index=False)

                st.download_button("Download CSV", data=csv, file_name="data.csv", mime="text/csv")
    except Exception as e:
        st.error(f"An error occurred: {e}")
