import requests

def savefile(url,path):
    r=requests.get(url)
    with open(path, "wb") as f:
        f.write(r.content)
url=input("Enter the url of website: ")

savefile(url,"Data.html")