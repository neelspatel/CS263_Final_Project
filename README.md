# CS263_Final_Project

This is the code used to scrape Github's search API to aggregate repositories that may contain sensitive secret keys, such as 
API keys and passwords. It also contains a module to pull these repositories and search through all past versions for secret keys
that may havre been committed in the past and were not scrubbed.

github.py is mainly a utilties file, exposing the function pull_results, which when give a query string to run against the github
search API will pull all resulting repositories that have a seciton of code possibly containing the secret key being searched on
by the query. If pull_results is run with the "save" flag it will dump all the html files corresponding to search result pages and 
repository home pages into a tar file as it sees them. Furhtermore pull_results may run in an inconsistent amount of time as it 
dynamically introduces dealy and routes through proxies to get around server-side rate limits. It is dependent on user_agents.txt.

check_github.py is what we ran to generate comprehensive results of queries (stored in results.txt) as it pull the repositories
resulting from various searches and then searches through all past commits for areas in which passwords strings may have been
scrubbed. It can be run by simply typing python check_github.py, the query that it runs on Github as well as constants related 
to the scrape timng and the maximum number of results pages to pull must be hardcoded in the file for now.

results.txt provides an easily searchable dump of the repositories and their relevant code segments which our heuristics identify
as having a high probability of containing secrets. This dump can be easily fed to regular expression and cleanup scripts to 
reveal which ones are exposing possibly harmful information.

