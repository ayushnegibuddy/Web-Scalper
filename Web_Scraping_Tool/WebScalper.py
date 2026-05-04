import requests
from bs4 import BeautifulSoup
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

def scrap_data(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        body = soup.body
        if not body:
            return pd.DataFrame()

        sections = []
    
        current = {"heading": "No Heading", "paragraphs": [], "links": []}

        for tag in body.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p']):
            if tag.name.startswith("h"):
                if current['paragraphs']:
                    sections.append(current)
                current = {
                    "heading": tag.get_text(" ", strip=True),
                    "paragraphs": [],
                    "links": []
                }
            elif tag.name == 'p':
                text = tag.get_text(" ", strip=True)
                if text:
                    current["paragraphs"].append(text)
                    for a in tag.find_all('a', href=True):
                        href = a['href']
                        current["links"].append(href)

        if current['paragraphs']:
            sections.append(current)

        return pd.DataFrame(sections)

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return pd.DataFrame()

def plot_content_distribution(df):
    df['num_paragraphs'] = df['paragraphs'].apply(len)
    df['num_links'] = df['links'].apply(len)

    fig, ax = plt.subplots(figsize=(10, 6))
    headings = df['heading']
    p_counts = df['num_paragraphs']
    l_counts = df['num_links']

    ax.barh(headings, p_counts, label='Paragraphs')
    ax.barh(headings, l_counts, left=p_counts, label='Links', color='orange')
    ax.set_xlabel("Count")
    ax.set_title("Content Distribution by Heading")
    ax.legend()
    plt.tight_layout()
    st.pyplot(fig)

st.set_page_config(page_title="Web Scraper", layout="wide")
st.title("Web Scraper")

url = st.text_input("Enter Website URL", "https://en.wikipedia.org/wiki/World_War_II")

if st.button("Scrape"):
    if not url:
        st.error("Please enter a real URL.")
    else:
        df = scrap_data(url)
        if df.empty:
            st.error("Website doesn't support web scalper or the site can't be read.")
        else:
            st.success(f"Scraped {len(df)} content sections.")

            for _, row in df.iterrows():
                with st.expander(row["heading"]):
                    for para in row["paragraphs"]:
                        st.markdown(para)
                    if row["links"]:
                        st.markdown("**Links:**")
                        for link in set(row["links"]):
                            st.markdown(f"- [{link}]({link})")

            plot_content_distribution(df)

            export_df = df.copy()
            export_df['paragraphs'] = export_df['paragraphs'].apply(lambda x: "\n".join(x))
            export_df['links'] = export_df['links'].apply(lambda x: ", ".join(set(x)))
            csv = export_df.to_csv(index=False)
            st.download_button("Download CSV", data=csv, file_name="data.csv", mime="text/csv")
