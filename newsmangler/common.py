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

"""Various miscellaneous useful functions."""

NM_VERSION = '0.1.3git'

import os
import sys
import logging

try:
	#Python version <3.x
	from ConfigParser import ConfigParser
except ImportError:
	from configparser import ConfigParser

def setupLogger(debug=False):
	logHandler = logging.getLogger() # gives us the "root" handler

	logHandler.setLevel(logging.DEBUG if debug else logging.INFO)
	
	debug_formatStr = '%(asctime)s [%(levelname)-5s][%(name)-11s] %(message)s'
	info_formatStr = '%(asctime)s [%(levelname)-5s] %(message)s'
	formatter = logging.Formatter(debug_formatStr if debug else info_formatStr)
	
	streamHandler = logging.StreamHandler()
	streamHandler.setFormatter(formatter)
	
	logHandler.addHandler(streamHandler)
	

def ParseManglerConfig(cfgfile='~/.newsmangler.conf'):
	logger = logging.getLogger('common')
	
	configFile = os.path.expanduser(cfgfile)
	if not os.path.isfile(configFile):
		raise IOError('Config file "%s" is missing!' % (configFile))
	
	logger.info('Using config file: "%s"' % configFile)
	
	parser = ConfigParser()
	parser.read(configFile)
	
	manglerConfDict = {}
	for section in parser.sections():
		manglerConfDict[section] = {}
		for option in parser.options(section):
			v = parser.get(section, option)
			if v.isdigit():
				v = int(v)
			manglerConfDict[section][option] = v
	
	return manglerConfDict


# ---------------------------------------------------------------------------
# Come up with a 'safe' filename
def SafeFilename(filename):
	safe_filename = os.path.basename(filename)
	
	#@todo: replace through re.sub(r'[\s\t]', '', filename)
	for char in [' ', "\\", '|', '/', ':', '*', '?', '<', '>']:
		safe_filename = safe_filename.replace(char, '_')
	return safe_filename

# ---------------------------------------------------------------------------
# Return a nicely formatted size
MB = 1024.0 ** 2
def NiceSize(byteValue):
	if byteValue < 1024:
		return '%dB' % (byteValue)
	elif byteValue < MB:
		return '%.1fKB' % (byteValue / 1024.0)
	else:
		return '%.1fMB' % (byteValue / MB)

# Return a nicely formatted time
def NiceTime(seconds):
	hours, left = divmod(seconds, 60 ** 2)
	mins, secs = divmod(left, 60)
	if hours:
		return '%dh %dm %ds' % (hours, mins, secs)
	else:
		return '%dm %ds' % (mins, secs)
