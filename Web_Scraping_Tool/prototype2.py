import requests
from bs4 import BeautifulSoup
import pandas as pd
import streamlit as st

def scrape_to_df(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    data = []

    for level in range(1, 7):
        for tag in soup.find_all(f'h{level}'):
            text = tag.get_text(strip=True)
            if text:
                data.append({'type': f'h{level}', 'content': text})

    for p in soup.find_all('p'):
        text = p.get_text(strip=True)
        if text:
            data.append({'type': 'paragraph', 'content': text})

    for a in soup.find_all('a', href=True):
        href = a['href']
        data.append({'type': 'link', 'content': href})

    return pd.DataFrame(data)

st.set_page_config(page_title="Web Scraper", layout="wide")
st.title(" Simple Web Scraper")

url = st.text_input("Enter a URL to scrape", "https://en.wikipedia.org/wiki/World_War_II")

if st.button("Scrape"):
    with st.spinner("Scraping..."):
        try:
            df = scrape_to_df(url)
            st.success(f"Scraped {len(df)} elements.")

            st.subheader(" Headings")
            for _, row in df[df['type'].str.contains('h')].iterrows():
                st.markdown(f"**• {row['content']}**")

            st.subheader(" Paragraphs")
            for i, row in df[df['type'] == 'paragraph'].iterrows():
                st.markdown(f" {row['content']}\n")

            st.subheader(" Links")
            link_df = df[df['type'] == 'link']
            st.dataframe(link_df.reset_index(drop=True))

            csv = df.to_csv(index=False)
            st.download_button(
                label="Download Full CSV",
                data=csv,
                file_name="data.csv",
                mime="text/csv"
            )
        except Exception as e:
            st.error(f"Error: {e}")
