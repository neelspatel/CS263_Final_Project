import requests
import sys
import urllib
import urllib2
from bs4 import BeautifulSoup
from optparse import OptionParser
import random
import os
import tarfile
from time import sleep
import math
import pymongo, json

import check_github


def send_log(log):
    print "sending error log"
    data = {
        "key": "***",
        "message": 
        {   "text": log,
            "subject": "Scraper Failed",
            "from_email": "***",
            "from_name": "Repo Scraper",
            "to": [{"email": "***"}]
        },
        "async": "false"
    }
    encoded_data = json.dumps(data)
    # TODO check for failure of failure log (haha)
    urllib2.urlopen('https://mandrillapp.com/api/1.0/messages/send.json', encoded_data)

# Pull all languages we are searching on into an array from the language file
def get_languages(all_lang=False):
    language_file = "languages.txt"
    if all_lang:
        language_file = "all_languages.txt"
    with open(language_file, "r") as lang_file:
        array = []
        for cur_line in lang_file:
            array.append(urllib.quote_plus(cur_line.rstrip('\n')))
    return array

def get_searches():
    search_file = "searches.txt"
    with open(search_file, "r") as searches:
        array = []
        for cur_line in searches:
            array.append(urllib.quote_plus(cur_line.rstrip('\n')))
    return array

# Select a random user agent uniformly from the file as the rate limit for github seems to be based off of this
def random_useragent():
    ua_file = open('user_agents.txt', 'r')
    cur_line = next(ua_file)
    for i, new_line in enumerate(ua_file):
        if random.randrange(i + 2): 
            continue
        cur_line = new_line
    return cur_line.rstrip('\n')

# Send a get request with a randomized user agent and delay (which can be turned off), if proxy is set to true, send it through an appropirate rotating proxy to
# circumvent ip based rate limiting
def obfuscated_request(request_string, proxy=False):
    headers = {'User-Agent': random_useragent()}
    print "sending "+request_string
    if proxy:
        auth = requests.auth.HTTPProxyAuth('username', 'password')
        proxies = {'http': 'http://us-ca.proxymesh.com:31280'}
        return requests.get(request_string, proxies = proxies, headers = headers).text
    else:
        return requests.get(request_string, headers = headers).text

def safe_scrape(req_str):
    got_results = False
    attempts = 1
    sleep(random.randint(2,4))
    while attempts < 5:
        try:
            # if attempts <5:
            response = obfuscated_request(req_str)
            # else:
            #   response = obfuscated_request(req_str, True)
            return response
        except Exception as e:
            print str(e)
            print "BUSTED. We will wait till our ip is probably out of jail"

            # Wait till we are no longer "suspicious" according to github.
            # We can perform 10 requests per minute when unauthenticated, 
            # so this wait should be sufficient on average
            sleep(attempts * random.randint(6,10))
            attempts += 1
    print "Failed on this one"
    raise Exception("github shut us down")


def recon_request(query, language):
    page = safe_scrape('https://github.com/search?l='+language+'&p=1&q='+str(query)+'&type=Code&ref=searchresults&utf8=%E2%9C%93')
    soup = BeautifulSoup(page)
    results_tabs = soup.findAll("span", { "class" : "counter" })
    for tab in results_tabs:
        if 'Code' in tab.parent.text:
            num_results = int(float(tab.text.replace(',','')))
        return num_results, page
    return 0, page


def process_html(html_dumps):
    repo_file_links = []
    for dump in html_dumps:
        soup = BeautifulSoup(dump)
        results = soup.find_all('p','title')
        for result in results:
            repo_link, file_link = result.find_all('a', href=True)
            repo_file_links.append([repo_link['href'], file_link['href']])
    return repo_file_links

def is_in_db(query, language):
    client = pymongo.MongoClient("mongodb://aran:aran1025@ds047020.mongolab.com:47020/personal-analytics")
    db = client.get_default_database()
    repos = db['repo_stats'].find_one({'search':query, 'language':language})
    return repos

def write_to_db(query, language, num_results, dumps):
    client = pymongo.MongoClient("mongodb://aran:aran1025@ds047020.mongolab.com:47020/personal-analytics")
    db = client.get_default_database()
    db['repo_stats'].insert({'search':query, 'language':language, 'results':num_results, 'links': dumps})

def pull_results(query, language):
    enc_query = urllib.quote_plus(query)
    html_dumps = []
    num_results, html = recon_request(enc_query, language)
    html_dumps.append(html)
    if num_results == 0:
        print "no results for "+language
        return None
    
    num_pages = min(int(math.ceil(num_results/10.0)), 100)
    if num_pages > 1:
        for page in range(2, num_pages+1):
            print "pulling page "+ str(page) + " of " + str(num_pages)
            html_dumps.append(safe_scrape('https://github.com/search?l='+language+'&p='+str(page)+'&q='+str(enc_query)+'&type=Code&ref=searchresults&utf8=%E2%9C%93'))

    print "processing blobs"
    repo_link_list = process_html(html_dumps)

    print "writing stats to db"
    write_to_db(query, language, num_results, repo_link_list)
    
    print "writing blobs to disk"
    keepcharacters = (' ','.','_')
    raw_filename = str(query)+str(language)+'.tar.bz2'
    filename = "".join(c for c in raw_filename if c.isalnum() or c in keepcharacters).rstrip()
    html_tar = tarfile.open(filename, 'w:bz2')
    for i, dump in enumerate(html_dumps):
        path = str(i)+'.html'
        with open(path, "w") as tmp:
            tmp.write(dump)
            tmp.close()
            html_tar.add(path)
            os.remove(path)
    html_tar.close()

    return repo_link_list


for search in get_searches():
    for language in get_languages():
        repos = is_in_db(search, language)
        if repos:                                       
            for url, search in repos["links"]:
                check_github.check_repo("https://github.com" + url, search.split("+"))



