import requests, os, time, subprocess, sys
from bs4 import BeautifulSoup

wget = True

def dump_thread(link, board_sfx):
    img_links = []

    soup = BeautifulSoup(requests.get(link).text, "html.parser")
    htm_links = [x.get('href') for x in soup.find_all("a") if x.get('href') is not None]
    
    for htm in htm_links:
        if htm.startswith(f'/{board_sfx}/src/') and htm.endswith(('.jpg', '.png', '.gif', '.swf')): # /azu/src/1316779210367.jpg
            img_links.append('http://ii.yakuji.moe' + htm)
    
    img_links = list(set(img_links)) # remove duplicates
    _dir = os.listdir()

    if wget:
        img_links.insert(0, '-nc')
        img_links.insert(0, 'wget')
        subprocess.run(img_links)
        return

    for img in img_links:
        print(img)
        
        # check dubs
        filename = img[img.rfind('/')+1:] 
        if filename in _dir: 
            continue
    
        while True:
            try:
                with requests.get(img) as request:
                    if request:
                        with open(filename, 'wb') as file:
                            file.write(request.content)
                    else:
                        print(f'/\ bad={request.status_code}')
                break
            except Exception as ex:
                print(f'{filename}: {str(ex)}    ')
                time.sleep(5)

        time.sleep(0.1)

def dump(_url, _from, _to):
    if 'html' in _url: # 'http://ii.yakuji.moe/azu/5.html'
        _url = os.path.dirname(_url) # 'http://ii.yakuji.moe/azu'

    board_sfx = _url[_url.rfind("/")+1:] # azu
    _range = [x for x in range(_from, _to)]

    os.makedirs(board_sfx, exist_ok=True)
    os.chdir(board_sfx)

    soup = BeautifulSoup(requests.get(_url).text, "html.parser")

    page_sfx = ['index.html']
    for sp in soup.find_all("a"):
        if '.html' in str(sp) and len(sp.get('href')) < 10: # 9999
            page_sfx.append(sp.get('href'))

    threads = []
    for sfx in page_sfx:
        if page_sfx.index(sfx) not in _range:
            continue

        soup = BeautifulSoup(requests.get(f'{_url}/{sfx}').text, "html.parser")
        htm_links = [x.get('href') for x in soup.find_all("a") if x.get('href') is not None] 

        for htm in htm_links:
            if htm.startswith('./res/') and htm.endswith('.html') : #'./res/10992.html'
                threads.append(_url + htm[1:])

        print(threads)
        print(f'{page_sfx.index(sfx) + 1} / {len(page_sfx)}', end = '\r')   
        time.sleep(1)

    for thread in threads:
        num = thread[thread.rfind('/')+1:-5]
        os.makedirs(num, exist_ok=True)
        os.chdir(num)

        print(f'({threads.index(thread) + 1} / {len(threads) }) {thread}', end = '      \n')
        dump_thread(thread, board_sfx)
        time.sleep(1)

        os.chdir('..')

    os.chdir('..')

if len(sys.argv) < 3:
    print(sys.argv[0], "startpage-endpage <link to board>")
    print(sys.argv[0], "0-5 http://ii.yakuji.moe/azu")
    sys.exit()

_from, _to = sys.argv[1].split('-')

for i in range(2, len(sys.argv)):  
    dump(sys.argv[i], int(_from), int(_to))
