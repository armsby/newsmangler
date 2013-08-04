#!/usr/bin/env python
# ---------------------------------------------------------------------------
# Copyright (c) 2005-2012 freddie@wafflemonster.org
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import os
import sys
import logging
from optparse import OptionParser

from newsmangler.common import parseManglerConfig, setupLogger, NM_VERSION
from newsmangler.postmangler import PostMangler

#class InputDataValidator
def parseCmdLineOption():
	# Parse our command line options
	parser = OptionParser(usage='usage: %prog [options] dir1 dir2 ... dirN')
	parser.add_option('-c', '--config',
		dest='config',
		help='Specify a different config file location',
	)
	parser.add_option('-f', '--files',
		dest='files',
		help='Assume all arguments are filenames instead of directories, and use SUBJECT as the base subject',
		metavar='SUBJECT',
	)
	parser.add_option('-g', '--group',
		dest='group',
		help='Post to a different group than the default',
	)
	parser.add_option('-d', '--debug',
		dest='debug',
		action='store_true',
		default=False,
		help="Enable debug logging",
	)
	parser.add_option('--profile',
		dest='profile',
		action='store_true',
		default=False,
		help='Run with the hotshot profiler (measures execution time of functions)',
	)

	(options, args) = parser.parse_args()
	
	# No args? We have nothing to do!
	if not args:
		parser.print_help()
		sys.exit(1)
		
	return (options, args)
	
def getPostSources(options, args):
	logger = logging.getLogger('mangler')
	
	# Make sure at least one of the args exists
	sourcesToPost = []
	if options.files:
		for arg in args:
			if os.path.isfile(arg):
				sourcesToPost.append(arg)
			else:
				logger.error('"%s" does not exist or is not a file!' % (arg))
	else:
		#it's a folder
		for arg in args:
			if os.path.isdir(arg):
				sourcesToPost.append(arg)
			else:
				logger.error('"%s" does not exist or is not a file!' % (arg))
	
	if not sourcesToPost:
		logger.error('No valid arguments provided on command line!')
		sys.exit(1)
	
	logger.debug("SourcesToPost: %s" % str(sourcesToPost) )
	return sourcesToPost 

def getPostTitle(options, args):
	postTitle = options.files if options.files else None
		
	return postTitle

def getValidNewsgroupName(options, manglerConfDict):
	from re import sub
	logger = logging.getLogger('mangler')
	
	# Make sure the group is ok
	if options.group:
		if '.' not in options.group:
			newsgroup = manglerConfDict['aliases'].get(options.group)
			if not newsgroup:
				logger.error('Group alias "%s" does not exist!' % (options.group))
				sys.exit(1)
		else:
			newsgroup = options.group
	else:
		newsgroup = manglerConfDict['posting']['default_group']
	
	# Strip whitespace from the newsgroup list to obey RFC1036
	newsgroup = sub(r'[\s\t]', '', newsgroup)
	
	return newsgroup

def main():
	(options, args) = parseCmdLineOption()
	setupLogger(options.debug)
	
	logger = logging.getLogger('mangler')
	logger.info("Welcome to newsMangler v%s" % NM_VERSION)
	
	resourceToPost = getPostSources(options, args)
	post_title = getPostTitle(options, args)
	
	# Parse our configuration file
	DEFAULT_CFG_FILE = '~/.newsmangler.conf'
	manglerConf = parseManglerConfig(options.config if options.config else DEFAULT_CFG_FILE)
	
	newsgroup = getValidNewsgroupName(options, manglerConf)
	
	# And off we go
	poster = PostMangler(manglerConf, debug=options.debug)
	
	if options.profile:
		import hotshot
		prof = hotshot.Profile('profile.poster')
		prof.runcall(poster.post, newsgroup, resourceToPost, post_title=post_title)
		prof.close()
		
		import hotshot.stats
		stats = hotshot.stats.load('profile.poster')
		stats.strip_dirs()
		stats.sort_stats('time', 'calls')
		stats.print_stats(25)
	
	else:
		poster.post(newsgroup, resourceToPost, post_title=post_title)

# ---------------------------------------------------------------------------

if __name__ == '__main__':
	main()
