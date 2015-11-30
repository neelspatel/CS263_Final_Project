import requests
import sys
import urllib
from bs4 import BeautifulSoup
from optparse import OptionParser
import random
import os
import tarfile
from time import sleep

# Tar ball for saving all the html files we pull
html_tar = tarfile.open('html_dumps.tar.bz2', 'w:bz2')

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
def obfuscated_request(request_string, delay=True, proxy=False):
	headers = {'User-Agent': random_useragent()}
	if delay:
		sleep(random.randint(1,3))
	if proxy:
		auth = requests.auth.HTTPProxyAuth('username', 'password')
		proxies = {'http': 'http://us-ca.proxymesh.com:31280'}
		return requests.get(request_string, proxies = proxies, headers = headers).text
	else:
		return requests.get(request_string, headers = headers).text

# Saves an html page to a file name and then dumps it into the tar ball (to save the data to disk for later perusal)
def save_result(filename, contents):
	with open(filename, "w") as tmp:
		tmp.write(contents)
		tmp.close()
		html_tar.add(filename)
		os.remove(filename)

# Gagues the popularity of a given repository based on the number of commits
def mine_repo_info(repo_link):
	response = obfuscated_request(repo_link)
	soup = BeautifulSoup(response)
	clone_url = soup.find('input', 'input-mini').get('value')
	meta_list = soup.find_all('span', 'num')
	repo_meta = {'commits': int(float(meta_list[0].text.replace(",", ""))), 'branches':int(float(meta_list[1].text.replace(",", "")))}
	return response, clone_url, repo_meta

# Comb all result pages for a certain query (up to a maximum of 100), with the save param determining whether or not to log all
# pages crawled to disk
def pull_results(query, save=False):
	result_list=[]
	for page in range(1, 100):
		got_results = False
		attempts = 1

		while got_results == False and attempts < 5:

			print "On page", page
			try:
				enc_query = urllib.quote_plus(query)
				response = obfuscated_request('https://github.com/search?utf8=%E2%9C%93&p='+str(page)+'&q='+str(enc_query)+'&type=Code&ref=searchresults')
				if save:
					save_result(enc_query+'-page-'+str(page)+'.html', response)
				soup = BeautifulSoup(response)
				results = soup.find_all('p','title')
				for result in results:
					repo_link, file_link = result.find_all('a', href=True)
					repo, clone_url, repo_meta = mine_repo_info('https://github.com'+repo_link['href'])
					if save:
						save_result(repo_link['href'].replace('/', '-')+'.html', repo)
					# print clone_url, query, repo_meta
					result_list.append([clone_url, query, repo_meta])
				got_results = True
			except Exception as e:
				print str(e)
				print "BUSTED. We will wait till our ip is out of jail"

				# Wait till we are no longer "suspicious" according to github.
				# We can perform 10 requests per minute when unauthenticated, 
				# so this wait should be sufficient
				sleep(attempts * 10)

			attempts += 1

	return result_list


if __name__ == '__main__':
	parser = OptionParser()
	parser.add_option("-q", "--query", dest="query", default=None,
			help="The search query to issue on github (literally the exact same thing you put in the github search box)")
	parser.add_option("-s", "--save", dest="save", default=False,
			help="The search query to issue on github")
	(options, args) = parser.parse_args()

	reload(sys)
	sys.setdefaultencoding("utf8")
	
	if options.query is not None:
		if options.save:
			print pull_results(options.query, True)
		else:
			print pull_results(options.query)


