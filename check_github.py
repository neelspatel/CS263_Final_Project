import os
import json
import github
import pymongo
import urllib

BASE_URL = 'https://github.com'

# Pull all languages we are searching on into an array from the language file
def get_file(l_file):
	with open(l_file, "r") as p_file:
	    array = []
	    for cur_line in p_file:
	        array.append(urllib.quote_plus(cur_line.rstrip('\n')))
	return array


#formats the secret line which we've read from the repo by removing leading + and -, tabs, and newlines
def clean_secret_line(line):
	if line[0] == "+":
		line = line[1:]
	elif line[0] == "-":
		line = line[1:]

	#removes leading tabs
	line = line.lstrip()

	line = line.replace("\n", "")

	return line
	
def is_in_db(query, language):
	client = pymongo.MongoClient("mongodb://aran:aran1025@ds047020.mongolab.com:47020/personal-analytics")
	db = client.get_default_database()
	repos = db['repo_stats'].find_one({'search':query, 'language':language})
	return repos

#checks the given repo URL for values of the given secret variable
def check_repo(url, secret):
	print "checking "+url+" with secret "+secret
	try:
		#clone the repo			
		os.system("git clone " + url)

		#enter the cloned repo
		name = url.split("/")[-1]
		name = name.replace(".git", "")

		os.chdir(name)

		#gets the changed lines
		os.system("git log -S'" + secret + "' -p > secret.txt")

		#find the lines containing secret
		with open("secret.txt") as f:
			lines = f.readlines()		

		secret_lines = [line for line in lines if secret in line]

		os.chdir("../")
		os.system("rm -rf " + name)

		#removes leading -, +, and tabs from the lines
		secret_lines = map(clean_secret_line, secret_lines)

		secret_lines = list(set(secret_lines))

		return secret_lines
	except:
		return []

#checks each of a list of repos, where each repo contains a 
#URL, query (secret variable to search for), and other metadata
def check_urls(urls):
	with open("results.txt", "a") as outputfile:
		for url_object in urls:
			#format of output:
			#	url
			#	query
			#	data
			#		list of passwords

			url, query, metadata = url_object

			print "Checking ", url, query

			outputfile.write(url + "\n")
			outputfile.write(query + "\n")
			outputfile.write(json.dumps(metadata) + "\n")

			secret_lines = check_repo(url, query)
			for line in secret_lines:
				outputfile.write(line + "\n")

			outputfile.write("\n")

languages = get_file("all_languages.txt")
searches = get_file("searches.txt")
print len(languages)
print len(searches)

for query in searches:
	for language in languages:
		repos = is_in_db(query, "PHP")
		for link in repos['links']:
			print check_repo(BASE_URL+link[0]+'.git', query)
		break
	break


# check_urls(urls)


