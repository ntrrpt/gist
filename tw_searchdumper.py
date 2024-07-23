#!/usr/bin/env python3
from __future__ import print_function
import time, sys, json, subprocess, tempfile, os, pathlib, optparse, psutil, random, string, pause
from datetime import datetime, timedelta
from twikit import Client
from loguru import logger

# search_tweet => 1 search in 18-20 seconds, 50 searches in 15 minutes
SEARCH_TWEET_DELAY = 30
TIMEOUT_DELAY = 60 * 2
DROP_SEARCH_AFTER_X_ATTEMPTS = 1
ARIA2_FILENAME = ''.join(random.choice(string.ascii_letters) for x in range(10)) + '.txt'
MAX_THREADS = 2

parser = optparse.OptionParser()
parser.add_option('-s', dest='search',   default='lucky star', help='search string')
parser.add_option('-y', dest='years',    default='10-24',      help='years interval (from-to, 10-24)')
parser.add_option('-m', dest='months',   default='1-12',       help='month interval (from-to, 1-12)')
parser.add_option('-d', dest='days',     default='1,15',       help='days (1,15)')
options, arguments = parser.parse_args()

aria2c_args = [
    'aria2c',
    f'--input-file={ARIA2_FILENAME}',
    f'--dir={options.search}',
    '--max-connection-per-server=1',
    '--auto-file-renaming=false',
    '--remote-time=true',
    '--log-level=error',
    '--console-log-level=error',
    '--download-result=hide'
]

logger.remove(0)
logger.add(
    sys.stderr, backtrace = True, diagnose = True,
    format = "<level>[{time:HH:mm:ss}]</level> {message}",
    colorize = True, level = 5
)

def childCount():
    current_process = psutil.Process()
    children = current_process.children()
    return(len(children))

def fileDel(filename):
    rem_file = pathlib.Path(filename)
    rem_file.unlink(missing_ok=True)

def add(dir, bin):
    with open(dir, 'a', encoding='utf-8') as file:
        file.write(bin + '\n')

def con(dict, c):
    for d in dict:
        if d in str(c):
            return True

def rqst_client():
    # "Illegal header value" bypass
    while True:
        try:
            client = Client('en-US')
            client.load_cookies('cookies.json')
            client.get_user_by_id('44196397')
            logger.info('client ok!')
            break
        except Exception as ex:
            if not con(['Illegal header value'], ex):
                logger.error('exc => ' + str(ex))
                sys.exit()
            time.sleep(1)
            print()

    return client

def picsdump(all_tweets):
    images = []
    dubs = 0

    for tw in all_tweets:
        if not tw.media:
            continue

        elif 'type' in tw.media[0] and 'video' in tw.media[0]['type']: # video
            url = tw.media[0]['video_info']['variants'][-1]['url']
            if url.find('?') != -1:
                url = url[:url.find('?')] # foo.mp4?bar=12 => foo.mp4
            img = [url, tw.user.screen_name]

        elif 'media_url_https' in tw.media[0]: # photo
            img = [tw.media[0]['media_url_https'], tw.user.screen_name]

        else:
            continue

        if img[0] in all_urls:
            dubs += 1
        else:
            all_urls.append(img[0])
            images.append(img)

    if not images:
        return '' # only dubs

    fileDel(ARIA2_FILENAME)

    # aria2c download list
    for img in images:
        add(
            ARIA2_FILENAME, 
            f'{img[0]}\n    out={img[1]} {os.path.basename(img[0])}'
        )

    subprocess.Popen(aria2c_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    ret_str = f'+{len(images)}'
    if dubs:
        ret_str += f' ~{dubs}'

    return f'{ret_str}'

def searchdump(search_str):
    def status(str):
        print(str, end=' ', flush=True)

    tweets = None
    all_tweets = []
    zero_searches = 0

    for first_search in (1, 0):
        while True:
            try:
                tweets = client.search_tweet(search_str, 'Media') if first_search else tweets.next()
                zero_searches = (zero_searches + 1) if not tweets else 0
                status(len(tweets))
                all_tweets += list(tweets)

                if zero_searches >= DROP_SEARCH_AFTER_X_ATTEMPTS:
                    break

                time.sleep(SEARCH_TWEET_DELAY + random.randint(-10,10))

                if first_search:
                    break

            except Exception as ex:
                if con(['Rate limit'], ex):
                    status('r')
                    pause.until(ex.rate_limit_reset + 5)

                elif con(['timed out', 'getaddrinfo'], ex): # rip internet
                    status('t')
                    time.sleep(TIMEOUT_DELAY)
                    
                elif con(['items'], ex): # no pics in first search
                    return

                elif con(['moduleItems'], ex): # no pics in second search
                    break

                elif con([
                'list index out of range', 
                'views', 
                'is_translatable', 
                'legacy',
                'Multiple cookies exist with name',
                'object has no attribute'], ex): # idk
                    time.sleep(TIMEOUT_DELAY)
                    break

                else:
                    logger.error(f'tw exc => {str(ex)}')
                    sys.exit()

    print('', end='\r', flush=True)
    logger.success(f'{search_str} {picsdump(all_tweets)}        ')
    return True

stop = False
all_urls = []
client = rqst_client()

_from, _to = options.years.split('-')
years = [x for x in range(int(_from), int(_to) + 1)]

_from, _to = options.months.split('-')
months = [x for x in range(int(_from), int(_to) + 1)]

days = options.days.split(',')

for y in years:
    if int(y) < 10: y = '0' + str(y)

    for m in months:
        if int(m) < 10: m = '0' + str(m)

        for d in days:
            if int(d) < 10: d = '0' + str(d)
            
            while childCount() >= MAX_THREADS:
                time.sleep(1)

            if stop or not searchdump( f'{options.search} lang:ja until:20{y}-{m}-{d}'):
                break

            if datetime(int(f'20{y}'), int(m), int(d)) > datetime.now():
                stop = True

while childCount() > 0:
    time.sleep(1)
else:
    logger.info(f'all_urls => {len(all_urls)}')
    fileDel(ARIA2_FILENAME)