# based on https://gist.github.com/xatier/63bcdbe4b5ad7f93b0bf

import requests, os, time, subprocess, sys
from bs4 import BeautifulSoup

def dump(url):
    if 'htm' in url: # 'http://dat.2chan.net/r/5.htm'
        url = os.path.dirname(url) # 'http://dat.2chan.net/r'

    soup = BeautifulSoup(requests.get(url).text, "html.parser")

    page_sfx = ['futaba.htm']
    for sp in soup.find_all("a"):
        if 'accesskey=' in str(sp):
            page_sfx.append(sp.get('href'))

    threads = []
    for sfx in page_sfx:
        soup = BeautifulSoup(requests.get(f'{url}/{sfx}').text, "html.parser")
        htm_links = [x.get('href') for x in soup.find_all("a") if "res" in x.get('href')]
        for htm in htm_links:
            threads.append(f'{url}/{htm}')

        print(f'{page_sfx.index(sfx) + 1} / {len(page_sfx)}', end = '\r')   

    for thread in threads:
        print(f'{threads.index(thread) + 1} / {len(threads)}', end = '      \n')
        subprocess.run(["gallery-dl", thread])

for i in range(1, len(sys.argv)):
    dump(sys.argv[i])