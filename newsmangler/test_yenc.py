import unittest
#import time
from sys import version_info
	
from yenc import *
from yenc import _yenc_encodeEscaped

class TestYencoding(unittest.TestCase):
	def setUp(self):
		try:
			from cStringIO import StringIO
			self.postFile = StringIO()
		except ImportError:
			#python 3.x
			from io import BytesIO
			self.postFile = BytesIO()
	
	@unittest.skipIf(version_info < (3, 0), "python3 specific method")
	def test_yEncoding_Python3(self):
		yEncode_Python3(self.postFile, b"Hello world", 11)
		
		print( repr(self.postFile.getvalue()) )
		## yEnc-encoded 'Hello world'
		#b'r\x8f\x96\x96\x99J\xa1\x99\x9c\x96\x8e\r\n'
		
		#>>> yEncode_Python3(postfile, "0123456789", 11)
		#'a684c7c6'
		#>>> 
		#>>> postfile.getvalue()
		## yEnd-encoded '0...9'
		#'Z[\\]^_`abc\r\n'
		
	def test_yenc_encodeEscaped_basic(self):
		self.assertEqual(b'r\x8f\x96\x96\x99J\xa1\x99\x9c\x96\x8e', 
			_yenc_encodeEscaped(b'Hello world') )
		self.assertEqual('r\x8f\x96\x96\x99J\xa1\x99\x9c\x96\x8e', 
			_yenc_encodeEscaped('Hello world') )
		
	def test_yenc_encodeEscaped_specialChar(self):
		self.assertEqual(b'\x3d\x7d',
			_yenc_encodeEscaped(b'\x13') )
		
	def test_yEncode_CRC(self):
		self.assertEqual('8bd69e52', yEncode_Python3(self.postFile, b"Hello world", 11))

	
if __name__ == '__main__':
    unittest.main(verbosity=3)
