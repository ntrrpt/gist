#!/usr/bin/env python3
from __future__ import print_function
import time, sys, json, subprocess, tempfile, os, pathlib, optparse
from datetime import datetime, timedelta
from twikit import Client
from loguru import logger

# search_tweet => 1 search in 18-20 seconds, 50 searches in 15 minutes
SEARCH_TWEET_DELAY = 10
RATE_LIMIT_DELAY = 60 * 2
DROP_SEARCH_AFTER_X_ATTEMPTS = 1

parser = optparse.OptionParser()
parser.add_option('-s', dest='search',   default='lucky star', help='search string')
parser.add_option('-y', dest='years',    default='10-24',      help='years interval (from-to, 10-24)')
parser.add_option('-m', dest='months',   default='1-12',       help='month interval (from-to, 1-12)')
parser.add_option('-d', dest='days',     default='1,15',       help='days (1,15)')
options, arguments = parser.parse_args()

aria2c_args = [
    'aria2c',
    '--input-file=tmp.txt',
    f'--dir={options.search}',
    '--max-connection-per-server=2',
    '--auto-file-renaming=false',
    '--remote-time=true',
    '--log-level=error',
    '--console-log-level=error',
    '--download-result=hide'
]

day_sequences = [
    ['1,15'],
    ['1,10,20'],
    ['1,7,14,21,28'],
    ['1,5,10,15,20,25']
]

logger.remove(0)
logger.add(
    sys.stderr, backtrace = True, diagnose = True,
    format = "<level>[{time:HH:mm:ss}]</level> {message}",
    colorize = True, level = 5
)

def msg(*a, **ka):
    if a:
        a = [a[0]] + list(a[1:])
    print(*a, **ka, end='\r')

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
        if 'type' in tw.media[0] and 'video' in tw.media[0]['type']: # video
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

    rem_file = pathlib.Path("tmp.txt")
    rem_file.unlink(missing_ok=True)

    # aria2c download list
    for img in images:
        add('tmp.txt', f'{img[0]}\n    out={img[1]} {os.path.basename(img[0])}')

    subprocess.Popen(aria2c_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    ret_str = f'{len(images)} new'
    if dubs:
        ret_str += f', {dubs} dubs'

    return f'({ret_str})'

def searchdump(search_str):
    tweets = None
    all_tweets = []
    zero_searches = 0

    for first_search in (1, 0):
        while True:
            try:
                tweets = client.search_tweet(search_str, 'Media') if first_search else tweets.next()
                zero_searches = (zero_searches + 1) if not tweets else 0
                msg('tweets len =>', len(tweets))
                all_tweets += list(tweets)

                if zero_searches >= DROP_SEARCH_AFTER_X_ATTEMPTS:
                    break

                time.sleep(SEARCH_TWEET_DELAY)

                if first_search:
                    break

            except Exception as ex:
                if con(['Rate limit'], ex):
                    msg('rate limited       ')
                    time.sleep(RATE_LIMIT_DELAY)

                elif con(['timed out', 'items'], ex): # no pics in first search
                    logger.warn(f'{search_str} (no pics)')
                    time.sleep(SEARCH_TWEET_DELAY)
                    return

                elif con(['moduleItems'], ex): # no pics in second search
                    break

                elif con(['views', 'is_translatable', 'legacy'], ex): # idk
                    time.sleep(RATE_LIMIT_DELAY)
                    break

                else:
                    logger.error(f'tw exc => {str(ex)}')
                    sys.exit()

    logger.success(f'{search_str} {picsdump(all_tweets)}')
    return True

stop = False
all_urls = list()
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

            if stop or not searchdump( f'{options.search} lang:ja until:20{y}-{m}-{d}'):
                break

            if datetime(int(f'20{y}'), int(m), int(d)) > datetime.now():
                stop = True

logger.info(f'all_urls => {len(all_urls)}')
