import requests
from bs4 import BeautifulSoup
import pandas as pd

def scrape_to_csv(url):
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

    df = pd.DataFrame(data)
    df.to_csv('scraped_data.csv', index=False, encoding='utf-8')
    print(" Data saved to scraped_data.csv")

scrape_to_csv('https://en.wikipedia.org/wiki/World_War_II')
