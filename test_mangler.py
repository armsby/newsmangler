import unittest
import time

try:
	import xml.etree.cElementTree as ET
except:
	import xml.etree.ElementTree as ET

#from newsmangler import asyncnntp

from newsmangler.article import Article
from newsmangler.common import *


class DummyFileWrapper:
	def __init__(self):
		self.set_returnStr()
	
	def set_returnStr(self, newByteString = b'Hello world'):
		self.returnStr = newByteString
	
	def read_part(self, begin, end):
		return self.returnStr

class TestArticle(unittest.TestCase):	
	def setUp(self):
		self.fileWrapper = DummyFileWrapper()
	    
		fileinfo = {
			'dirname': 'post_title',
			'filename': 'real_filename',
			'filepath': 'filepath',
			'filesize': 123456,
			'parts': 2,
		}
		
		# setup enviroment variable
		self.conf = {}
		self.conf['server'] = {'hostname':'test.Host'}
		self.conf['posting'] = {'from' : 'testFrom@Account'}
		self.newsgroup = 'test.Newsgroup'
		subject = 'testSubject [1/3] - "testFile" yEnc (1/1)'
		partnum = fileinfo['parts']
		
		self.art = Article(self.fileWrapper, 0, 3, fileinfo, subject, partnum)
		
		self.art.headers['From'] = self.conf['posting']['from']
		self.art.headers['Newsgroups'] = self.newsgroup
		self.art.headers['Subject'] = subject #% (partnum)
		self.art.headers['Message-ID'] = '<%.5f.%d@%s>' % (time.time(), partnum, self.conf['server']['hostname'])
		self.art.headers['X-Newsposter'] = 'newsmangler %s (%s) - https://github.com/madcowfred/newsmangler\r\n' % \
				('0.0.1', 'yenc.yEncMode()')

	
	def test_article(self):
		self.art.prepare()
		
		ioRepresentation = self.art.postfile
		print(ioRepresentation.getvalue())
	
	def test_test(self):
	    print(self.fileWrapper.read_part(1,2))
	    #r––™J¡™œ–Ž4
	
	
from newsmangler.yenc import yEncode_Python
class TestYencoding(unittest.TestCase):
	def setUp(self):
		try:
			from cStringIO import StringIO
			self.postFile = StringIO()
		except ImportError:
			#python 3.x
			from io import BytesIO
			self.postFile = BytesIO()
	
	def test_yEncoding_Python(self):
		yEncode_Python(self.postFile, b"Hello world", 11)
		
		print(self.postFile.getvalue())
		#b'r\x8f\x96\x96\x99J\xa1\x99\x9c\x96\x8e\r\n'
		
	def test_yEncode_CRC(self):
		self.assertEqual('8bd69e52', yEncode_Python(self.postFile, b"Hello world", 11))
	#def test_sample(self):
	#    with self.assertRaises(ValueError):
	#        random.sample(self.seq, 20)
	#    for element in random.sample(self.seq, 5):
	#        self.assertTrue(element in self.seq)
	
	#    self.assertEqual(self.seq, range(10))
	# should raise an exception for an immutable sequence
	#    self.assertRaises(TypeError, random.shuffle, (1,2,3))
	
if __name__ == '__main__':
    unittest.main(verbosity=2)
