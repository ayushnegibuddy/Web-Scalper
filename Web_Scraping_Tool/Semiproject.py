import requests
from bs4 import BeautifulSoup
import pandas as pd
import streamlit as st

def structured_scrape(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    data = []
    current_heading = "No Heading"
    current_section = {"heading": "", "paragraphs": [], "links": []}

    for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'a']):
        if tag.name.startswith('h'):
            if current_section["paragraphs"] or current_section["links"]:
                data.append(current_section)
            current_heading = tag.get_text(strip=True)
            current_section = {"heading": current_heading, "paragraphs": [], "links": []}

        elif tag.name == 'p':
            text = tag.get_text(strip=True)
            if text:
                current_section["paragraphs"].append(text)

        elif tag.name == 'a' and tag.get('href'):
            current_section["links"].append(tag['href'])

    if current_section["paragraphs"] or current_section["links"]:
        data.append(current_section)

    return pd.DataFrame(data)

st.set_page_config(page_title="Simple Web Scraper", layout="wide")
st.title("Simple Web Scraper")
st.caption("Scrapes headings with their associated paragraphs and links.")

url = st.text_input("Enter a URL", "https://en.wikipedia.org/wiki/World_War_II")

if st.button("Scrape"):
    with st.spinner("Scraping and grouping..."):
        try:
            df = structured_scrape(url)
            st.success(f"Found {len(df)} sections.")

            for _, row in df.iterrows():
                with st.expander(row['heading']):
                    for para in row['paragraphs']:
                        st.markdown(para)
                    if row['links']:
                        st.markdown("**Links:**")
                        for link in row['links']:
                            st.markdown(f"- [{link}]({link})")

            export_df = df.copy()
            export_df['paragraphs'] = export_df['paragraphs'].apply(lambda x: "\n".join(x))
            export_df['links'] = export_df['links'].apply(lambda x: ", ".join(x))
            csv = export_df.to_csv(index=False)

            st.download_button("Download CSV", data=csv, file_name="grouped_scraped_data.csv", mime="text/csv")
        except Exception as e:
            st.error(f"Error: {e}")
