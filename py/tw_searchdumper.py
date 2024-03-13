#!/usr/bin/env python3
import time, sys, json, subprocess, tempfile, os, pathlib, optparse
from twikit import Client
from loguru import logger

# search_tweet => 1 search in 18-20 seconds, 50 searches in 15 minutes
SEARCH_TWEET_DELAY = 10
RATE_LIMIT_DELAY = 60 * 2
DROP_SEARCH_AFTER_X_ATTEMPTS = 1

aria2c_args = [
    'aria2c',
    '--input-file=tmp.txt',
    '--dir=output',
    '--max-connection-per-server=5',
    '--auto-file-renaming=false',
    '--remote-time=true',
    '--log-level=error',
    '--console-log-level=error',
    '--download-result=hide'
]

parser = optparse.OptionParser()
parser.add_option('-s', dest='search',   default='lucky star', help='search string')
parser.add_option('-y', dest='years',    default='10-24',      help='years interval (from-to, 10-24)')
parser.add_option('-m', dest='months',   default='1-12',       help='month interval (from-to, 1-12)')
parser.add_option('-d', dest='days',     default='1,15',       help='days (1,15)')
options, arguments = parser.parse_args()

logger.remove(0)
logger.add(
    sys.stderr,
    backtrace = True,
    diagnose = True,
    format = "<level>[{time:DD-MMM-YYYY HH:mm:ss}]</level> {message}",
    colorize = True,
    level = 5
)

def text_append(dir, bin):
    with open(dir, 'a', encoding='utf-8') as file:
        file.write(bin + '\n')

def rqst_client():
    # "Illegal header value" bypass
    while True:
        try:
            client = Client('en-US')
            client.load_cookies('cookies.json')
            client.get_user_by_id('44196397')
            break
        except Exception as ex:
            if not 'Illegal header value' in str(ex):
                logger.error('exc =>' + str(ex))
                sys.exit()
            time.sleep(1)
            print()

    return client

def picsdump(all_tweets):
    images = []

    for tweet in all_tweets:
        if 'media_url_https' not in tweet.media[0]:
            continue

        img = [tweet.media[0]['media_url_https'], tweet.user.screen_name]

        if img[0] not in all_urls:
            all_urls.append(img[0])
            images.append(img)

    if not images:
        logger.info('no images in list')
        return

    rem_file = pathlib.Path("tmp.txt")
    rem_file.unlink(missing_ok=True)

    # aria2c download list
    for img in images:
        text_append('tmp.txt', f'{img[0]}\n    out={img[1]} {os.path.basename(img[0])}')

    subprocess.Popen(aria2c_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    logger.success(f'sent {len(images)} images')

def searchdump(search_str):
    tweets = None
    all_tweets = []
    zero_searches = 0

    for first_search in (1, 0):
        while True:
            try:
                tweets = client.search_tweet(search_str, 'Media') if first_search else tweets.next()
                zero_searches = (zero_searches + 1) if not tweets else 0
                logger.info(f'tweets len => {len(tweets)}')
                all_tweets += list(tweets)

                if zero_searches >= DROP_SEARCH_AFTER_X_ATTEMPTS:
                    break

                time.sleep(SEARCH_TWEET_DELAY)

                if first_search:
                    break

            except Exception as ex:
                logger.error('exc => ' + str(ex))
                if 'items' in str(ex): # no pics in first search
                    time.sleep(SEARCH_TWEET_DELAY)
                    return
                elif 'moduleItems' in str(ex): # no pics in second search
                    break
                elif 'Rate limit exceeded' in str(ex):
                    time.sleep(RATE_LIMIT_DELAY)
                elif 'timed out' in str(ex):
                    time.sleep(RATE_LIMIT_DELAY)
                elif 'views' in str(ex): # idk
                    time.sleep(RATE_LIMIT_DELAY)
                else:
                    sys.exit()

    picsdump(all_tweets)
    print()

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

            search_str = f'{options.search} lang:ja until:20{y}-{m}-{d}'
            logger.warning(search_str)
            searchdump(search_str)

logger.success(f'all_urls => {len(all_urls)}')