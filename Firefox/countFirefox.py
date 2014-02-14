import sqlite3 as sql
import datetime
import sys
import json
import subprocess
from pickle import dump, load
from urlparse import urlparse

# This script stores the number of opened tabs in Firefox and the URL of the current selected tab if Firefox is focused. The script should be called quite often, as the visit time is only counted in steps between calls of the script
# Known bugs/limitations:
# * Does not work if multiple Firefox windows are open (then we would need to get the info which window is focused)
# * Suspended or standby (if the uptime was not reset to zero) is not detected, the time will be counted as if the computer was running all the time (only a problem if Firefox is focused on the first run of the script)

# loosely based on https://stackoverflow.com/questions/15884363/in-mozilla-firefox-how-do-i-extract-the-number-of-currently-opened-tabs-to-save
# sessionstore.js is created with this code:https://hg.mozilla.org/integration/fx-team/file/2b9e5948213f/browser/components/sessionstore/src/SessionStore.jsm

# lastAccessed was introduced in this Bugzilla entry: https://bugzilla.mozilla.org/show_bug.cgi?id=739866


def loadSessionJSON(sessionfile):
	global j
	j = json.loads(open(sessionfile, 'rb').read().decode('utf-8'))

def getOpenedFirefoxTabs():
	all_tabs = list(map(tabs_from_windows, j['windows']))
	return sum(map(len, all_tabs))

def info_for_tab(tab):
	try:
		return (tab['entries'][0]['url'], tab['entries'][0]['title'])
	except IndexError:
		return None
	except KeyError:
		return None

def tabs_from_windows(window):
	return list(map(info_for_tab, window['tabs']))

def getAccessedDateOfTab(tab):
	# lastAccessed is set with Javascripts Date.now() which is in milliseconds, Pythons timestamp is in seconds
	print str(tab['index'])+": "+tab['entries'][0]['url']+" was accessed "+str(-(datetime.datetime.fromtimestamp(tab['lastAccessed']/1000)-datetime.datetime.now()).total_seconds()) +" seconds ago.";
	return None;

def getPathToDB():
	return '/home/florin/bin/QuantifiedSelf/Firefox/firefoxProcesses.db'

def saveToDatabase():
	con = None
	try:

		con = sql.connect(getPathToDB())
		cur = con.cursor()
		loadSessionJSON('/home/florin/.mozilla/firefox/3wxc4x2q.default/sessionstore.js');
		cur.execute("INSERT OR REPLACE INTO firefox VALUES (?,?,?)", (datetime.datetime.now().strftime("%s"), 'standard', getOpenedFirefoxTabs()));
		con.commit();
		#map(getAccessedDateOfTab, j['windows'][0]['tabs']);

		# check if foreground window belongs to Firefox
		cmdline = subprocess.Popen('/home/florin/bin/QuantifiedSelf/Firefox/getForegroundWindow.sh', stdout=subprocess.PIPE).stdout.read().strip();
		print "Current foreground process is "+cmdline;
		if cmdline.find('firefox') != -1 or cmdline.find('kate') != -1:
			# index for selected tab is off by one: https://hg.mozilla.org/integration/fx-team/file/2b9e5948213f/browser/components/sessionstore/src/SessionStore.jsm#l2822
			# *        Index of selected tab (1 is first tab, 0 no selected tab)
			#print "The url "+j['windows'][0]['tabs'][j['windows'][0]['selected']-1]['entries'][0]['url'] + " is opened.";
			# get hostname
			parsedUrl = urlparse(j['windows'][0]['tabs'][j['windows'][0]['selected']-1]['entries'][0]['url']);
			hostname = parsedUrl.hostname;
			print "A site on host "+hostname+" is opened";

			# get seconds since last run
			try:
				tempFile = open('stor.temp', 'r');
				lastRun = load(tempFile);
				tempFile.close();
			except (OSError, IOError, TypeError, EOFError, IndexError) as e:
				#on any expectable error, don't count this run
				lastRun = datetime.datetime.now();

			print "last run was on "+str(lastRun);

			diff = (datetime.datetime.now() - lastRun);

			print str(diff.total_seconds()) + " seconds ago";


			# if this time is longer than the uptime, the computer was shut off between runs => use uptime as diff length
			#TODO(wasMitNetzen): read uptime file directly
			uptime = datetime.timedelta(0, int(subprocess.Popen('/bin/cat /proc/uptime | grep -oP "^[0-9]*"', shell=True, stdout=subprocess.PIPE).stdout.read().strip()));
			print "Uptime: " + str(uptime.total_seconds());
			if uptime > diff:
				diff = uptime;

			# check if hostname has already an entry

			# if not, make new entry

			#
		f = open('stor.temp', 'w');
		now = datetime.datetime.now();
		#print "dumping "+str(now);
		dump(now, f);
		f.close()



	except sql.Error, e:
		print "Error %s:" % e.args[0]
		sys.exit(1)

	finally:
		if con:
			con.close()

if __name__ == '__main__':
	saveToDatabase()
