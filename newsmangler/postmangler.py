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

"""Main class for posting stuff."""

import asyncore
import select
import time
import sys
import logging
import os

try:
    import xml.etree.cElementTree as ET
except:
    import xml.etree.ElementTree as ET

from newsmangler import asyncnntp
from newsmangler import yenc
from newsmangler.article import Article
from newsmangler.common import NM_VERSION, niceFileSize_str, niceTime_str, safeFilename
from newsmangler.filewrap import FileWrap

class PostMangler:
    def __init__(self, conf, debug):
        self.conf = conf
        
        self._conns = []
        self._idle = []
        
        self.logger = logging.getLogger('postMangler')
        
        # Create a poll object for async bits to use. If the user doesn't have
        # poll, we're going to have to fake it.
        try:
            asyncore.poller = select.poll()
            self.logger.debug('Using select.poll() for sockets')
        except AttributeError:
            from newsmangler.fakepoll import FakePoll
            asyncore.poller = FakePoll()
            self.logger.debug('Using FakePoll.poll() for sockets')

        self.conf['posting']['skip_filenames'] = self.conf['posting'].get('skip_filenames', '').split()
        
        self._articles = []
        self._files = {}
        self._msgids = {}
        
        self._current_dir = None
        self.newsgroup = None
        self.post_title = None
        
        # Some sort of useful logging junk about which yEncode we're using
        self.logger.debug('Using %s module for yEnc', yenc.yEncMode())
    
    # Connect all of our connections
    def connect(self):
        for i in range(self.conf['server']['connections']):
            conn = asyncnntp.AsyncNNTP(
                    parent = self, 
                    connid = i, 
                    host = self.conf['server']['hostname'],
                    port = self.conf['server']['port'], 
                    bindto = None, 
                    username = self.conf['server']['username'],
                    password = self.conf['server']['password'],
                    use_ssl = self.conf['server']['use_ssl']
            )
            conn.do_connect()
            self._conns.append(conn)

    # Poll our poll() object and do whatever is neccessary. Basically a combination
    # of asyncore.poll2() and asyncore.readwrite(), without all the frippery.
    def pollSocketEvents(self):
        results = asyncore.poller.poll(0)
        for fd, flags in results:
            obj = asyncore.socket_map.get(fd)
            if obj is None:
                self.logger.critical('Invalid FD for pollSocketEvents(): %d', fd)
                asyncore.poller.unregister(fd)
                continue
            
            try:
                if flags & (select.POLLIN | select.POLLPRI):
                    obj.handle_read_event()
                if flags & select.POLLOUT:
                    obj.handle_write_event()
                if flags & (select.POLLERR | select.POLLHUP | select.POLLNVAL):
                    obj.handle_expt_event()
            except (asyncore.ExitNow, KeyboardInterrupt, SystemExit):
                raise
            except:
                obj.handle_error()

    # -----------------------------------------------------------------------

    def post(self, newsgroup, postme, post_title=None):
        self.newsgroup = newsgroup
        self.post_title = post_title
        
        # Generate the list of articles we need to post
        self.generate_articleToPost_list(postme)
        
        validArticlesAvailable = bool(self._articles)
        if not validArticlesAvailable:
            self.logger.warning('No valid articles to post!')
            return
        
        self.connect()

        self.logger.info('Posting %d article(s)...', len(self._articles))

        # And post primary loop
        self._bytes = 0
        last_stuff = start = time.time()
        while True:
            now = time.time()
            
            # Poll our sockets for events
            self.pollSocketEvents()
            
            # Possibly post some more parts now
            while self._idle and self._articles:
                conn = self._idle.pop(0)
                article = self._articles.pop(0)
                conn.post_article(article)
            
            # Do some stuff every now and then
            if now - last_stuff >= 0.5:
                last_stuff = now
                
                for conn in self._conns:
                    conn.reconnect_check(now)
                
                if self._bytes:
                    interval = now - start
                    speed = self._bytes / interval / 1024
                    left = len(self._articles) + (len(self._conns) - len(self._idle))
                    sys.stdout.write('%d article(s) remaining - %.1fKB/s     \r' % (left, speed))
                    sys.stdout.flush()
            
            # All done?            
            allWorkersIdle = ( len(self._idle) == self.conf['server']['connections'])
            ArticlesLeft = ( len(self._articles) != 0 )
            if not ArticlesLeft and allWorkersIdle:
                interval = time.time() - start
                speed = self._bytes / interval
                self.logger.info('Posting complete - %s in %s (%s/s)',
                    niceFileSize_str(self._bytes), niceTime_str(interval), niceFileSize_str(speed))
                
                # If we have some msgids left over, we might have to generate
                # a .NZB
                if self.conf['posting']['generate_nzbs'] and self._msgids:
                    self.generate_nzb()
                
                break
            
            # And sleep for a bit to try and cut CPU chompage
            time.sleep(0.01)
    
    def remember_msgid(self, article_size, article):
        if self.conf['posting']['generate_nzbs']:
            if self._current_dir != article._fileinfo['dirname']:
                if self._msgids:
                    self.generate_nzb()
                    self._msgids = {}
                
                self._current_dir = article._fileinfo['dirname']
            
            subj = article._subject % (1)
            if subj not in self._msgids:
                self._msgids[subj] = [int(time.time())]
            #self._msgids[subj].append((article.headers['Message-ID'], article_size))
            self._msgids[subj].append((article, article_size))
    
    def generate_articleToPost_list(self, filesToPost):
        if self.post_title:
            # "files" mode is just one lot of files
            self._gal_prepare_files(
                    postTitle = self.post_title, 
                    files = filesToPost)
        else:
            # "dirs" mode could be a whole bunch
            for dirName in filesToPost:
                dirName = os.path.abspath(dirName)
                if not dirName:
                    continue
                
                self._gal_prepare_files(
                        postTitle = os.path.basename(dirName), 
                        files = os.listdir(dirName), 
                        basePath = dirName)
    
    # Do the heavy lifting for generate_articleToPost_list
    def _gal_prepare_files(self, postTitle, files, basePath=''):
        article_size = self.conf['posting']['article_size']
        
        goodFiles = self.filterGoodFiles(files, basePath)
        
        # Do stuff with files
        n = 1
        for filePath, fileName, fileSize in goodFiles:
            parts, partial = divmod(fileSize, article_size)
            if partial:
                parts += 1
            
            self._files[filePath] = FileWrap(filePath, parts)

            # Build a subject
            real_filename = os.path.split(fileName)[1]
            
            filenNumberFormatter = '%%0%sd' % len(str(len(files)))
            fileNum = filenNumberFormatter % n
            
            partCountFormatter = '%%0%sd' % len(str(parts))
            subject = '%s [%s/%d] - "%s" yEnc (%s/%d)' % (
                postTitle, fileNum, len(goodFiles), real_filename, partCountFormatter, parts
            )
            
            # Apply a subject prefix
            if self.conf['posting']['subject_prefix']:
                subject = '%s %s' % (self.conf['posting']['subject_prefix'], subject)
            
            # Now make up our parts
            fileinfo = {
                'dirname': postTitle,
                'filename': real_filename,
                'filepath': filePath,
                'filesize': fileSize,
                'parts': parts,
            }
            self.logger.debug("fileInfo: %s" % str(fileinfo))
            
            for i in range(parts):
                partnum = i + 1
                begin = i * article_size
                end = min(fileSize, partnum * article_size)
                
                article = self._build_article(self._files[filePath], begin, end, fileinfo, subject, partnum)
                self._articles.append(article)
            
            n += 1
    
    def filterGoodFiles(self, files, basePath):
        goodFiles = []
        for fileName in files:
            filePath = os.path.abspath(os.path.join(basePath, fileName))
            
            if not os.path.isfile(filePath):
                continue
            if fileName in self.conf['posting']['skip_filenames'] or fileName == '.newsmangler':
                continue
            fileSize = os.path.getsize(filePath)
            isFileEmpty = (fileSize == 0)
            if isFileEmpty:
                continue
            
            goodFiles.append((filePath, fileName, fileSize))
        
        goodFiles.sort()
        return goodFiles
    
    # Build an article for posting.
    def _build_article(self, fileWrapper, begin, end, fileinfo, subject, partnum):
        art = Article(fileWrapper, begin, end, fileinfo, subject, partnum)
        
        art.headers['From'] = self.conf['posting']['from']
        art.headers['Newsgroups'] = self.newsgroup
        art.headers['Subject'] = subject % (partnum)
        art.headers['Message-ID'] = '<%.5f.%d@%s>' % (time.time(), partnum, self.conf['server']['hostname'])
        art.headers['X-Newsposter'] = 'newsmangler %s (%s) - https://github.com/madcowfred/newsmangler\r\n' % (
            NM_VERSION, yenc.yEncMode())

        return art
    
    # -----------------------------------------------------------------------
    # Generate a .NZB file!
    def generate_nzb(self):
        filename = 'newsmangler_%s.nzb' % safeFilename(self._current_dir)

        self.logger.debug('Begin generation of %s', filename)

        gentime = time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())
        root = ET.Element('nzb')
        root.append( ET.Comment('Generated by newsmangler v%s at %s' % (NM_VERSION, gentime)) )

        for subject, msgids in self._msgids.items():
            posttime = msgids.pop(0)

            # file
            f = ET.SubElement(root, 'file',
                {
                    'poster': self.conf['posting']['from'],
                    'date': str(posttime),
                    'subject': subject,
                }
            )
            
            # newsgroups
            groups = ET.SubElement(f, 'groups')
            for newsgroup in self.newsgroup.split(','):
                group = ET.SubElement(groups, 'group')
                group.text = newsgroup
            
            # segments
            segments = ET.SubElement(f, 'segments')
            temp = [(m._partnum, m, article_size) for m, article_size in msgids]
            temp.sort()
            for partnum, article, article_size in temp:
                segment = ET.SubElement(segments, 'segment',
                    {
                        'bytes': str(article_size),
                        'number': str(partnum),
                    }
                )
                segment.text = str(article.headers['Message-ID'][1:-1])

        with open(filename, 'wb') as nzbfile:
            ET.ElementTree(root).write(nzbfile, xml_declaration=True)

        self.logger.info('Successfully generated the nzb file %s', filename)

# ---------------------------------------------------------------------------
