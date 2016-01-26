import os
import json
import subprocess
from threading import Thread
import re

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

def secrets_in_line(line, secrets, stopper_words=[]):	
	"""
	line is the input line
	secrets is a list of search terms
	stopper_words is a list of common placeholders
	returns True if an = sign exists (assignment) 
	OR any of the secrets are in the line
	AND none of the stopper words are in the line 
	"""
	# check if equal signs is 
	flag = '=' in line
	if not flag:
		return False
	
	flag = False
	for secret in secrets:
		flag = flag or (secret in line)  
	# check for stopper words
	for stopper_word in stopper_words:
		if stopper_word in line:
			return False
	return flag

# exclude things that look like environment variables 
def is_environment_var(line):
	"""
	True if looks like setting to environment variable
	"""
	return  ("env" in line) or ("ENV" in line)

class SubprocessTimeoutError(RuntimeError):
  """Error class for subprocess timeout."""
  pass

#from http://www.ostricher.com/2015/01/python-subprocess-with-timeout/
def run_command_with_timeout(cmd, timeout_sec, mute=False):
    """Execute `cmd` in a subprocess and enforce timeout `timeout_sec` seconds.
 
    Return subprocess exit code on natural completion of the subprocess.
    Raise an exception if timeout expires before subprocess completes."""
    if not mute:
    	proc = subprocess.Popen(cmd)
    else:
    	proc = subprocess.Popen(cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
    proc_thread = Thread(target=proc.communicate)
    proc_thread.start()
    proc_thread.join(timeout_sec)
    if proc_thread.is_alive():
        # Process still running - kill it and raise timeout error
        try:
            proc.kill()
        except OSError, e:
            # The process finished between the `is_alive()` and `kill()`
            return proc.returncode
        # OK, the process was definitely killed
        raise SubprocessTimeoutError('Process #%d killed after %f seconds' % (proc.pid, timeout_sec))
    # Process completed naturally - return exit code
    return proc.returncode

#checks the given repo URL for values of the given secret variable
def check_repo(url, secrets):
	print url, secrets

	#clone the repo			
	#os.system("git clone " + url)
	#subprocess.Popen(["git", "clone", url]).wait()		
	try:
		run_command_with_timeout(["git", "clone", url], 5, mute=True)

		#enter the cloned repo
		name = url.split("/")[-1]
		name = name.replace(".git", "")

		try:
			os.chdir(name)
		except:
			raise SubprocessTimeoutError("Directory not found")

		#gets the changed lines
		os.system("git log -S'" + "|".join(secrets) + "' -p --pickaxe-regex > secret.txt")

		#find the lines containing secret
		with open("secret.txt") as f:
			lines = f.readlines()

		secret_lines = [line for line in lines if secrets_in_line(line, secrets)]
		# filter lines that might be environment variables
		secret_lines = [line for line in secret_lines if not is_environment_var(line)]

		os.chdir("../")
		os.system("rm -rf " + name)

		#removes leading -, +, and tabs from the lines
		secret_lines = map(clean_secret_line, secret_lines)

		secret_lines = list(set(secret_lines))		

		#filter lines which have an extractable key
		find_secrets = ".*?(?:" + "|".join(secrets) + ").*?=\s?['\"](\w+?)['\"]"
		secret_lines = [re.findall(find_secrets, x) for x in secret_lines]
		#secret_lines = [re.findall(r"=\s?['\"](\w+?)['\"]", x) for x in secret_lines]		
		

		secret_lines = [x[0] for x in secret_lines if len(x) == 1]
		secret_lines = list(set(secret_lines))
		if secret_lines:
			print "Keys: ", secret_lines

		return secret_lines
	except SubprocessTimeoutError:
		print "Repo too big; moving on\n"

		name = url.split("/")[-1]
		name = name.replace(".git", "")
		os.system("rm -rf " + name)
		return None
	

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

			secret_lines = check_repo(url, ["secret", "key"])
			for line in secret_lines:
				outputfile.write(line + "\n")

			outputfile.write("\n")

'''
urls = [
	["https://github.com/ooola/ruggerfest", "SECRET_KEY", {"data": "test"}],
	["https://github.com/sqs/openelections", "WEBAUTH_SECRET", {"data": "test"}],
	["https://github.com/priestc/flightloggin2", "AWS_SECRET_KEY", {"data": "test"}],
	["https://github.com/hilliard/basic-auth", "GMAIL_PASSWORD", {"data": "test"}],
	["https://github.com/hecontreraso/crackplan", "GMAIL_PASSWORD", {"data": "test"}],
	["https://github.com/gdb/domaincli", "stripe_api_key", {"data": "test"}],
	["https://github.com/frank2workd/stripebank", "Stripe.api_key", {"data": "test"}],
	["https://github.com/bcackerman/stripeanalytics", "Stripe.api_key", {"data": "test"}],	
]
'''


#urls = [['https://github.com/zdot/django-boilerplate.git', 'SECRET_KEY', {'commits': 6, 'branches': 1}], ['https://github.com/imenetoumi/www_auf_org.git', 'SECRET_KEY', {'commits': 22, 'branches': 1}], ['https://github.com/robrechtdr/djangobox.git', 'SECRET_KEY', {'commits': 42, 'branches': 1}], ['https://github.com/robrechtdr/djangobox.git', 'SECRET_KEY', {'commits': 42, 'branches': 1}], ['https://github.com/ernestjumbe/django-bootstrap-template.git', 'SECRET_KEY', {'commits': 55, 'branches': 1}], ['https://github.com/yaph/flask-init.git', 'SECRET_KEY', {'commits': 22, 'branches': 1}], ['https://github.com/meowfreeze/django_startproject.git', 'SECRET_KEY', {'commits': 57, 'branches': 3}], ['https://github.com/ernestjumbe/django-scaffold.git', 'SECRET_KEY', {'commits': 49, 'branches': 1}], ['https://github.com/cottonwoodcoding/charles_ellsworth.git', 'SECRET_KEY', {'commits': 91, 'branches': 2}], ['https://github.com/ulope/django-template.git', 'SECRET_KEY', {'commits': 8, 'branches': 1}], ['https://github.com/justuswilhelm/senior-residence.git', 'SECRET_KEY', {'commits': 182, 'branches': 1}], ['https://github.com/bkuri/scatpod.git', 'SECRET_KEY', {'commits': 33, 'branches': 2}], ['https://github.com/polakj/Portfolio.git', 'SECRET_KEY', {'commits': 17, 'branches': 1}], ['https://github.com/marazmiki/django-project-template.git', 'SECRET_KEY', {'commits': 31, 'branches': 1}], ['https://github.com/PostTenebrasLab/PTL-Status-API.git', 'SECRET_KEY', {'commits': 70, 'branches': 1}], ['https://github.com/McPants/portfolio.git', 'SECRET_KEY', {'commits': 14, 'branches': 1}]]

#urls = github.pull_results("SECRET_KEY")
#print urls

#urls = [['https://github.com/zdot/django-boilerplate.git', 'SECRET_KEY', {'commits': 6, 'branches': 1}], ['https://github.com/imenetoumi/www_auf_org.git', 'SECRET_KEY', {'commits': 22, 'branches': 1}], ['https://github.com/robrechtdr/djangobox.git', 'SECRET_KEY', {'commits': 42, 'branches': 1}], ['https://github.com/robrechtdr/djangobox.git', 'SECRET_KEY', {'commits': 42, 'branches': 1}], ['https://github.com/ernestjumbe/django-bootstrap-template.git', 'SECRET_KEY', {'commits': 55, 'branches': 1}], ['https://github.com/yaph/flask-init.git', 'SECRET_KEY', {'commits': 22, 'branches': 1}], ['https://github.com/meowfreeze/django_startproject.git', 'SECRET_KEY', {'commits': 57, 'branches': 3}], ['https://github.com/ernestjumbe/django-scaffold.git', 'SECRET_KEY', {'commits': 49, 'branches': 1}], ['https://github.com/cottonwoodcoding/charles_ellsworth.git', 'SECRET_KEY', {'commits': 91, 'branches': 2}], ['https://github.com/ulope/django-template.git', 'SECRET_KEY', {'commits': 8, 'branches': 1}], ['https://github.com/justuswilhelm/senior-residence.git', 'SECRET_KEY', {'commits': 182, 'branches': 1}], ['https://github.com/bkuri/scatpod.git', 'SECRET_KEY', {'commits': 33, 'branches': 2}], ['https://github.com/marazmiki/django-project-template.git', 'SECRET_KEY', {'commits': 31, 'branches': 1}], ['https://github.com/polakj/Portfolio.git', 'SECRET_KEY', {'commits': 17, 'branches': 1}], ['https://github.com/PostTenebrasLab/PTL-Status-API.git', 'SECRET_KEY', {'commits': 70, 'branches': 1}], ['https://github.com/McPants/portfolio.git', 'SECRET_KEY', {'commits': 14, 'branches': 1}], ['https://github.com/kazu634/chef.git', 'SECRET_KEY', {'commits': 738, 'branches': 9}], ['https://github.com/justuswilhelm/senior-residence.git', 'SECRET_KEY', {'commits': 182, 'branches': 1}], ['https://github.com/bkuri/scatpod.git', 'SECRET_KEY', {'commits': 33, 'branches': 2}], ['https://github.com/marazmiki/django-project-template.git', 'SECRET_KEY', {'commits': 31, 'branches': 1}], ['https://github.com/polakj/Portfolio.git', 'SECRET_KEY', {'commits': 17, 'branches': 1}], ['https://github.com/PostTenebrasLab/PTL-Status-API.git', 'SECRET_KEY', {'commits': 70, 'branches': 1}], ['https://github.com/McPants/portfolio.git', 'SECRET_KEY', {'commits': 14, 'branches': 1}], ['https://github.com/kazu634/chef.git', 'SECRET_KEY', {'commits': 738, 'branches': 9}], ['https://github.com/pyprism/Hiren-Books.git', 'SECRET_KEY', {'commits': 104, 'branches': 1}], ['https://github.com/minimill/cerberus.git', 'SECRET_KEY', {'commits': 28, 'branches': 1}], ['https://github.com/LaMustax/skilleton.git', 'SECRET_KEY', {'commits': 11, 'branches': 1}], ['https://github.com/danrschlosser/isaaclevien.com.git', 'SECRET_KEY', {'commits': 8, 'branches': 1}], ['https://github.com/y2bishop2y/vagrant.flask.git', 'SECRET_KEY', {'commits': 5, 'branches': 1}], ['https://github.com/A-Estudiar/aestudiar_backend.git', 'SECRET_KEY', {'commits': 11, 'branches': 1}], ['https://github.com/tobbez/lys-reader.git', 'SECRET_KEY', {'commits': 118, 'branches': 1}], ['https://github.com/LukeHoersten/snaplet-postmark.git', 'SECRET_KEY', {'commits': 7, 'branches': 1}], ['https://github.com/greenmoon55/cntrains.git', 'SECRET_KEY', {'commits': 79, 'branches': 1}], ['https://github.com/MapStory/mapstory-geonode.git', 'SECRET_KEY', {'commits': 556, 'branches': 9}], ['https://github.com/nickray22/lafitte_mop.git', 'SECRET_KEY', {'commits': 5, 'branches': 1}], ['https://github.com/logandhead/flask-vagrant-puppet-boilerpate.git', 'SECRET_KEY', {'commits': 4, 'branches': 1}], ['https://github.com/theowni/encryptedSession-PHP.git', 'SECRET_KEY', {'commits': 3, 'branches': 1}], ['https://github.com/shea256/flask-app-generator.git', 'SECRET_KEY', {'commits': 40, 'branches': 1}], ['https://github.com/henriquebastos/dj-kickstart.git', 'SECRET_KEY', {'commits': 20, 'branches': 1}], ['https://github.com/catalyst/basil.git', 'SECRET_KEY', {'commits': 103, 'branches': 2}], ['https://github.com/clayman74/essential.git', 'SECRET_KEY', {'commits': 29, 'branches': 2}], ['https://github.com/matheusho/eventex.git', 'SECRET_KEY', {'commits': 83, 'branches': 1}], ['https://github.com/deis/example-spree.git', 'SECRET_KEY', {'commits': 1, 'branches': 1}], ['https://github.com/voltnor/pyChaos.git', 'SECRET_KEY', {'commits': 8, 'branches': 1}], ['https://github.com/develersrl/shorturl.git', 'SECRET_KEY', {'commits': 43, 'branches': 1}], ['https://github.com/jetsgit/fedtax.git', 'SECRET_KEY', {'commits': 3, 'branches': 1}], ['https://github.com/anaerobeth/dev-group-project.git', 'SECRET_KEY', {'commits': 16, 'branches': 1}]]





#print check_repo()
#print check_repo("https://github.com/ooola/ruggerfest", "SECRET_KEY")
#print check_repo("https://github.com/sqs/openelections", "WEBAUTH_SECRET")
#print check_repo("https://github.com/elections/openelections", "WEBAUTH_SECRET")

#this repo has thousands of flight details, and contains a secret key
#print check_repo("https://github.com/priestc/flightloggin2", "AWS_SECRET_KEY")

#these repos have a gmail email and password
#print check_repo("https://github.com/hilliard/basic-auth", "GMAIL_PASSWORD")
#print check_repo("https://github.com/hecontreraso/crackplan", "GMAIL_PASSWORD")

#this has a Stripe API key, but may be garbage value
#print check_repo("https://github.com/gdb/domaincli", "stripe_api_key")

#this has a Stripe API key, but are sk_test_XXXXXX values
#print check_repo("https://github.com/frank2workd/stripebank", "Stripe.api_key")
#print check_repo("https://github.com/bcackerman/stripeanalytics", "Stripe.api_key")









