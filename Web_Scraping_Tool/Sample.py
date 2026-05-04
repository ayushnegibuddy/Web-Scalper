import requests
from bs4 import BeautifulSoup

with open("sample.html", "r") as file:
    html_content = file.read()
soup = BeautifulSoup(html_content, "html.parser")
print(soup.title.string)

for link in soup.find_all("a"):
    print(link.get("href"))
    print(link.get_text())
print(soup.find_all("h1"))
