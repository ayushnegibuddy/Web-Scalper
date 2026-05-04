import requests
import pandas as pd
from bs4 import BeautifulSoup

url = 'https://en.wikipedia.org/wiki/World_War_II'  
response = requests.get(url)

soup = BeautifulSoup(response.text, 'html.parser')
table = soup.find('table')

data = pd.read_html(str(table))[0]

print(data)
