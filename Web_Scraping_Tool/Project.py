import requests
from bs4 import BeautifulSoup
import pandas as pd
import streamlit as st
from urllib.parse import urljoin

def simple_scrape(url):
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

st.set_page_config(page_title="Simple Wiki Scraper", layout="wide")
st.title("Simple Web Scraper")

url = st.text_input("Wikipedia URL", "https://en.wikipedia.org/wiki/World_War_II")

if st.button("Scrape"):
    try:
        df = simple_scrape(url)
        st.success(f"Scraped {len(df)} sections.")

        for _, row in df.iterrows():
            with st.expander(row["heading"]):
                for p in row["paragraphs"]:
                    st.markdown(p)
                for l in set(row["links"]):
                    st.markdown(f"- [{l}]({l})")

        export_df = df.copy()
        export_df['paragraphs'] = export_df['paragraphs'].apply(lambda x: "\n".join(x))
        export_df['links'] = export_df['links'].apply(lambda x: ", ".join(set(x)))
        csv = export_df.to_csv(index=False)

        st.download_button("Download CSV", data=csv, file_name="wiki_data.csv", mime="text/csv")
    except Exception as e:
        st.error(f"Error: {e}")
