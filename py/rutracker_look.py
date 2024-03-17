#!/usr/bin/env python3
import time
import threading
import sys
import os, re, pyrfc6266
import json
import datetime
import requests
import optparse
import re
import hashlib, psutil
from loguru import logger
import schedule
import shutil
import subprocess
from http.cookiejar import MozillaCookieJar
import pathlib
from contextlib import suppress
from bs4 import BeautifulSoup

def add(dir, bin):
    with open(dir, 'a', encoding='utf-8') as file:
        file.write(bin + '\n')

def ntfy(url):
    with suppress(Exception):
        title = 'Torrent updated!'
        soup = BeautifulSoup(requests.get(url).text, "html.parser")

        requests.post(
            "https://ntfy.sh/" + options.ntfy_id, timeout=10,
                data = soup.title.string.encode(encoding='utf-8'),
                headers = {
                    "title": title.encode(encoding='utf-8'),
                    "click": url.encode(encoding='utf-8')
                }
        )

def netscape_cookies(filename):
    cookie_jar = requests.cookies.RequestsCookieJar()

    cookies = MozillaCookieJar(filename)
    cookies.load(ignore_expires=True, ignore_discard=True)
    cookie_jar.update(cookies)

    return cookie_jar

def get_hash(url, save_to=''):
    hash = None
    if url.find("?t=") != -1:
        url = f'https://rutracker.org/forum/dl.php{url[url.find("?t="):]}'
    
    with requests.get(url, cookies=netscape_cookies(options.cookies_file)) as request:
        if request:
            output = request.content
         
            if '<!DOCTYPE html>' not in str(output):
                hash = hashlib.md5(output).hexdigest()
            else:
                logger.warning(f'[html returned] {url}')
                return
            
            if save_to:
                filename = pyrfc6266.parse_filename(request.headers['Content-Disposition'])
                os.makedirs(save_to, exist_ok=True)

                with open(f"{save_to}/{filename}", 'wb') as file:
                    file.write(output)

    return hash

def dump_list(input):
    _list = {}
    with open(input) as file:
        for line in file:
            url = ''
            hash = 'null'

            line = line.rstrip()
            if len(line) > 1:
                split = line.split()
                url = split[0]
                if len(split) > 1:
                    hash = split[1]

            _list[len(_list)] = {
                'url': line if (not url or line[0] == '#') else url,
                'hash': '' if (not url or line[0] == '#') else hash
            }

    return _list

def check_torrents():
    changed = False
    tr_list = dump_list(options.list_file)

    for i in range(len(tr_list)):
        url = tr_list[i]["url"]
        if not url or url[0] == "#": # comment or empty
            continue
        
        md5hash = get_hash(url)
        if not md5hash:
            logger.error(f'[none returned] {url}')
            continue

        if tr_list[i]["hash"] != md5hash:
            tr_list[i]["hash"] = md5hash
            changed = True

            logger.success(f'[hash changed] {url}')

            if options.ntfy_id: 
                ntfy(url)

            if options.save_dir:
                get_hash(url, options.save_dir)

    if changed:
        rem_file = pathlib.Path(options.list_file)
        rem_file.unlink(missing_ok=True)

        for i in range(len(tr_list)):
            add(options.list_file, f'{tr_list[i]["url"]} {tr_list[i]["hash"]}')

if __name__ == '__main__':
    logger.remove(0)
    logger.add(
        sys.stderr,
        backtrace = True,
        diagnose = True,
        format = "<level>[{time:HH:mm:ss}]</level> {message}",
        colorize = True,
        level = 5
    )

    parser = optparse.OptionParser()
    parser.add_option('-l', dest='list_file', default='tr_list.txt', help='list with rutracker links')
    parser.add_option('-c', dest='cookies_file', default='cookies.txt', help='cookies in netscape format')
    parser.add_option('-n', dest='ntfy_id', default='', help='ntfy.sh notifications')
    parser.add_option('-d', dest='save_dir', default='', help='save .torrent in dir after hashsum changed')
    parser.add_option('-s', dest='schedule', action='store_true', help='schedule (every hour)')
    options, arguments = parser.parse_args()
    logger.info('started')
    
    if not options.schedule:
        check_torrents()
    else:
        schedule.every().hour.at(":00").do(check_torrents)
        while True:
            schedule.run_pending()
    
    


