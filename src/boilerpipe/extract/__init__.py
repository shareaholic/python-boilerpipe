import jpype
import urllib2
import socket
import charade
import threading

socket.setdefaulttimeout(15)
lock = threading.Lock()

InputSource        = jpype.JClass('org.xml.sax.InputSource')
StringReader       = jpype.JClass('java.io.StringReader')
HTMLHighlighter    = jpype.JClass('de.l3s.boilerpipe.sax.HTMLHighlighter')
BoilerpipeSAXInput = jpype.JClass('de.l3s.boilerpipe.sax.BoilerpipeSAXInput')

class Extractor(object):
    """
    Extract text. Constructor takes 'extractor' as a keyword argument,
    being one of the boilerpipe extractors:
    - DefaultExtractor
    - ArticleExtractor
    - ArticleSentencesExtractor
    - KeepEverythingExtractor
    - KeepEverythingWithMinKWordsExtractor
    - LargestContentExtractor
    - NumWordsRulesExtractor
    - CanolaExtractor
    """
    extractor = None
    source    = None
    data      = None
    headers   = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:40.0) Gecko/20100101 Firefox/40.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Connection": "keep-alive"
    }
    
    def __init__(self, extractor='DefaultExtractor', **kwargs):

        if kwargs.get('logger'):
            self.logger = kwargs['logger']
        else:
            self.logger = None

        if kwargs.get('url'):
            request     = urllib2.Request(kwargs['url'], headers=self.headers)
            try:
                connection  = urllib2.urlopen(request)
            except:
                connection = None
                if self.logger is not None:
                    self.logger.exception( 'boilerpipe extractor failed on urlopen() for uri %s' % kwargs['url'] )

            if connection is not None:
                self.data   = connection.read()
                encoding    = connection.headers['content-type'].lower().split('charset=')[-1]
                if encoding.lower() == 'text/html':
                    encoding = charade.detect(self.data)['encoding']
                self.data = unicode(self.data, encoding)
            else:
                if self.logger is not None:
                    self.logger.debug('boilerpipe execution continues with empty document')
                self.data = u''

        elif kwargs.get('html'):
            self.data = kwargs['html']
            if not isinstance(self.data, unicode):
                self.data = unicode(self.data, charade.detect(self.data)['encoding'])
        else:
            raise Exception('No text or url provided')

        try:
            # make it thread-safe
            if threading.activeCount() > 1:
                if jpype.isThreadAttachedToJVM() == False:
                    jpype.attachThreadToJVM()
            lock.acquire()
            
            self.extractor = jpype.JClass(
                "de.l3s.boilerpipe.extractors."+extractor).INSTANCE
        finally:
            lock.release()
    
        reader = StringReader(self.data)
        self.source = BoilerpipeSAXInput(InputSource(reader)).getTextDocument()
        self.extractor.process(self.source)
    
    def getText(self):
        return self.source.getContent()
    
    def getHTML(self):
        highlighter = HTMLHighlighter.newExtractingInstance()
        return highlighter.process(self.source, self.data)
    
    def getImages(self):
        extractor = jpype.JClass(
            "de.l3s.boilerpipe.sax.ImageExtractor").INSTANCE
        images = extractor.process(self.source, self.data)
        jpype.java.util.Collections.sort(images)
        images = [
            {
                'src'   : image.getSrc(),
                'width' : image.getWidth(),
                'height': image.getHeight(),
                'alt'   : image.getAlt(),
                'area'  : image.getArea()
            } for image in images
        ]
        return images
