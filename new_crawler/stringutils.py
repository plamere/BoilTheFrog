import datetime
import hashlib
import htmlentitydefs
import logging
import random
import re
import string
import sys
import time
from types import BooleanType, FloatType, IntType, ListType, LongType, StringType, UnicodeType
import unicodedata
import uuid
import urllib

from chartable import simplerchars

COMMENT = re.compile(r'<!--.*?-->')

# doesn't handle higher range control chars - will interfere with unicode chars:
#  + range(127,160)
control_chars = ''.join(map(unichr, range(0,32)))
CONTROL_CHARS = re.compile('[%s]' % re.escape(control_chars))

logger = logging.getLogger(__name__)

class NestOpener(urllib.FancyURLopener):
    version = "nestReader/0.2 (discovery; http://the.echonest.com/reader.html; reader at echonest.com)"

def random_alphanumeric(length):
    chars = string.letters + string.digits
    return ''.join(random.choice(chars) for i in xrange(length))

def randomString(length=10):
    return ''.join(random.choice(string.letters) for x in xrange(length))

def randomType():
    return random.choice(["artist","track","release","doc"])

def randomInt(max=1000):
    return random.randint(0,max)

def randomFloat():
    return random.random()

def randomUUID():
    return str(uuid.uuid4())

def randomDocument():
    return {"name":randomString(15), "enid":randomUUID(), "type":randomType(), "grackleCount":randomInt(), "hotttnesss":randomFloat()}

def bandNameNormalize(name):
    # Does name normalization for myspace etc name matching
    out = name.lower()
    out = re.sub(r' group', '', out)
    out = re.sub(r' band', '', out)
    out = re.sub(r' and ', ' ', out)
    out = re.sub(r'\(.*?\)', '', out)
    out = re.sub(r'\[.*?\]', '', out)
    out = re.sub(r'[\-\,\.\&\$\%\!\@\#\*\:\"\'\?\;]',' ', out)
    out = re.sub(r'\ {2,}', ' ', out)
    out = re.sub(r'^ ', '', out)
    out = re.sub(r' $', '', out)
    out = re.sub(r'^the', '', out)
    out = re.sub(r'^ ', '', out)
    out = re.sub(r' $', '', out)
    out = out[:25]
    out = unaccent(out, erase_unrecognized=False)
    return out
    
def uncomma(s, dumb=False):
    if type(s) not in (StringType, UnicodeType):
        raise ValueError, "Argument must be a string."
    if ', ' not in s:
        return s

    if dumb:
        return re.sub('(.*?), ([^ ]*)', r'\2 \1', s)

    a, b = s.split(', ', 1)
    suffix = ''

    for amp in [' & ', ' And ', ' and ', ' AND ', ' / ', ' + ']:
        if amp in b:
            commable, suffix = b.split(amp, 1)
            suffix = amp + suffix
            return "%s %s%s" % (commable, a, suffix)
    return "%s %s" % (b, a) 

def str2bool(s):
    if(isinstance(s,bool)):
        return s
    if s in ['Y', 'y']:
        return True
    if s in ['N', 'n']:
        return False
    if s in ['True', 'true']:
        return True
    elif s in ['False', 'false']:
        return False
    else:
        raise ValueError, "Bool-looking string required."

def delist(item):
    if item == []:
        return ''
    if type(item) is ListType:
        return item[0]
    return item

def summarize_string(s, length=50):
    ss = str(s)
    if len(ss) > length:
        return '%s: %s ... [%s more chars]' % (type(s), ss[:length], len(ss) - length)
    else:
        return s

def reallyunicode(s, encoding="utf-8"):
    """
    Try the user's encoding first, then others in order; break the loop as 
    soon as we find an encoding we can read it with. If we get to ascii,
    include the "replace" argument so it can't fail (it'll just turn 
    everything fishy into question marks).
    
    Usually this will just try utf-8 twice, because we will rarely if ever
    specify an encoding. But we could!
    """
    if type(s) is StringType:
        for args in ((encoding,), ('utf-8',), ('latin-1',), ('ascii', 'replace')):
            try:
                s = s.decode(*args)
                break
            except UnicodeDecodeError:
                continue
    if type(s) is not UnicodeType:
        raise ValueError, "%s is not a string at all." % s
    return s

def reallyUTF8(s):
    return reallyunicode(s).encode("utf-8")

def unfancy(s):
    "Removes smartquotes, smartellipses, and nbsps. Always returns Unicode."
    simplerpunc = {145: "'", 146: "'", 147: '"', 148: '"', 133: '...', 160: ' ', 173: '-',
                   8211: "-", 8212: "--", 8216:"'", 8217: "'", 8220:'"', 8221:'"', 8222: '"', 8230: '...'}
    ret =  "".join([simplerpunc.get(ord(char), char) for char in reallyunicode(s)])
    return ret

def unaccent(s, erase_unrecognized=True):
    """Removes umlauts and accents, etc. Unless erase_unrecognized=False,
       any characters that don't have an ASCII simplified form are
       removed entirely."""
    ## The dict "simplerchars" is in another file because it's
    ## so huge. See import statement at top.
    if not isinstance(s,basestring):
        raise ValueError, "unaccent argument %s must be a string." % str(s)
    unistr = reallyunicode(s)
    ret = u''
    for c in unistr:
        if c in simplerchars:
            ret += simplerchars[c]
        else:
            decomp = unicodedata.normalize('NFKD', c)
            basechar = decomp[0]
            ## These will all be unicode characters, so
            ## technically none of them are in string.printable.
            ## But "in" uses equality, not identity, and
            ## since u'a' == 'a' it will all work out.
            if not erase_unrecognized or basechar in string.printable:
                ret += basechar
    return ret

def convertentity(m):
    """Convert a HTML entity into normal string (UTF-8)"""
    prefix, entity = m.groups()
    try:
        if prefix != '#':
            ## Look up name, change it to a unicode code point (integer).
            entity = htmlentitydefs.name2codepoint[entity]
        else:
            if entity.startswith('x'):
                entity = int(entity[1:], 16)
            else:
                entity = int(entity)
    except (KeyError, ValueError):
        ## Give back original unchanged.
        return "&%s%s;" % (prefix, entity)

    return unichr(int(entity))

def decode_htmlentities(string):
    """Uses converentity to convert a string containing
    HTML entitites in a  string into normal strings (UTF-8.)"""
    entity_re = re.compile("&(#?)(\d{1,5}|\w{1,8});")
    return entity_re.subn(convertentity, reallyunicode(string))[0]

def convertentities(s):
    """Convert a HTML quoted string into normal string (UTF-8).
    Works with &#XX; and with &nbsp; &gt; etc."""
    s = reallyunicode(s)
    rep = re.compile(r'&(#?)([a-zA-Z0-9]+?);')
    unquoted = rep.sub(convertentity,s)
    return unquoted

def unquotehtml(s):
    unquoted = convertentities(s)
    return unfancy(unquoted).encode('utf-8')

# YES I WANT TO CALL IT CHOMP
def chomp(str):
    return str.rstrip('\r\n')
    
def long_time(t=None):
    if t is None:
        t = datetime.datetime.now()
    st = datetime.datetime.isoformat(t)
    st = re.sub(r"[\-\:\.A-Za-z]","",st)
    st = st[0:17]
    return st

def solr_time(when=None):
    "Returns solr-specific UTC time string (1995-12-31T23:59:59.999Z)."
    if when is None:
        when = time.gmtime()
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', when)

timeToLongTime = long_time
timeToSolrTime = solr_time

def readable_time(t=None):
    "Returns second-accuracy time string suitable for sorting or reading by humans, like '2009-04-24-12-45-04'."
    if t is None:
        t = time.localtime()
    return time.strftime('%Y-%m-%d-%H-%M-%S', t)

def MD5(text):
    ## We will convert to UTF-8 if given Unicode, 
    ## BUT if fed a bytestring we just checksum it,
    ## so don't go MD5ing strings in encodings
    ## incompatible with UTF-8 and expecting it
    ## to work out okay!
    if type(text) == UnicodeType:
        sys.stderr.write("md5 of Unicode requested - encoding to UTF-8.\n")
        sys.stderr.write("text (asciified for display): %s\n" % ascii(text))
        text = text.encode('utf-8')    
    m = hashlib.md5()
    m.update(text)
    return m.hexdigest()
    
def parseEntererLine(line):
    line = line.rstrip("\r\n")
    s = line.split(' ### ')
    l = {}
    if(len(s) == 9):
        l["foreignID_AR"] = s[0]
        l["foreignID_RE"] = s[1]
        l["foreignID_TR"] = s[2]
        l["name_AR"] = s[3]
        l["name_RE"] = s[4]
        l["name_TR"] = s[5]
        l["type"] = s[6]
        l["tagname"] = s[7]
        l["tagvalue"] = s[8]
    else:
        logger.error("Can't parse line %s got %d out of it", line, len(s))
        l = None
    return l
    
def makeNiceLucene(text):
    #http://lucene.apache.org/java/docs/queryparsersyntax.html#Escaping%20Special%20Characters
    text = re.sub(r'\bAND\b', '\AND', text)
    text = re.sub(r'\bOR\b', '\OR', text)
    text = re.sub(r'\bNOT\b', '\NOT', text)
    return re.sub(r"([\+\-\&\|\!\(\)\{\}\[\]\;\^\"\~\*\?\:\\])",r"\\\1", text)

def normalizeString(text):
    "Does ryan mckinley text normalization"
    digitMap = ["zero","one","two","three","four","five","six","seven","eight","nine"]
    LOWASCII = range(0,128)
    charList = (['E', chr(129) ,',', 'f',  ',', '.', 't',  '+', '^', '%',  'S',  '<','D',  ' ', 'Z', ' ',  ' ',  '\'', '\'', '\"','\"', '-','-', '-',   '-',   ' ',   's',   '>',   'c',   ' ', 'z', 'Y',' ',  '!', 'c', 'L',  '.', 'Y', '|',  'S', '.', 'c',' ', '<',   '-', '-',  'R',  '-',  'o', '+', '.','3','\'', 'u',  'P','.',',', '1',  'o',  '>',  '.',  '.', ' ', '?',  'A',  'A','A',  'A', 'A',  'A',  'A',  'C','E', 'E', 'E', 'E',  'I','I', 'I', 'I',  'D',  'N', 'O', 'O','O','O',  'O',  'x','O','U','U',  'U', 'U', 'Y','P','B',  'a',  'a','a','a',  'a',  'a', 'A',  'c',  'e', 'e','e','e','i','i','i',  'i','o', 'n',  'o', 'o', 'o', 'o',  'o',  '/','o',  'u','u',  'u',  'u', 'y',  'p',  'y'])
    for c in charList:
        LOWASCII.append(ord(c))
    
    # Strip whitespace at ends
    r = text.strip().lower()
    r = re.sub(r"[\/\,\:\.\&\(\)\<\>\:\;\-\_\+]"," ",r)
    words = text.split()
    newphrase = []
    for w in words:
        if(w=="and" or w=="the" or w=="of" or w=="und"):
            pass
        else:
            newword = ""
            for c in w:
                if(ord(c)>1 and ord(c)<255):
                    c = chr(LOWASCII[ord(c)]).lower()
                    if(ord(c)>=ord('a') and ord(c) <= ord('z')):
                        newword = newword + c
                    if(ord(c)>=ord('0') and ord(c) <= ord('9')):
                        if(len(newword)>0):
                            newphrase.append(newword)
                        newphrase.append(digitMap[ord(c)-ord('0')])
            
            if(len(newword)>0):
                newphrase.append(newword)
    
    normalized = " ".join(newphrase)
    return normalized

def undo_wtf8(s):
    try:
        if type(s) == str:
            s2 = s.decode('utf-8')
        else:
            s2 = s
        s3 = s2.encode('raw-unicode-escape')
        s4 = s3.decode('utf-8')
        return s4
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s

def undo_windows_wtf8(s):
    try:
        if type(s) == str:
            s2 = s.decode('utf-8')
        else:
            s2 = s
        s3 = s2.encode('windows-1252')
        s4 = s3.decode('utf-8')
        return s4
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s

def utf8(text):
    return unicode(text, "utf8", errors="replace")

def ascii(text, errors='ignore'):
    if type(text) not in (StringType, UnicodeType):
        raise ValueError, "Argument %s must be string or Unicode!" % str(text)
    text = unaccent(text, erase_unrecognized=True)
    ## unaccent returns Unicode-- should be ascii safe, but
    ## in case it's not...
    return text.encode('ascii', errors)

def cleanup(text):
    ltRem = text.replace("\r","").replace("\n","")
    ltRem = re.sub(r" {2,}"," ",ltRem)
    ltRem = re.sub(r"\<.{1,20}\>","",ltRem)
    return ltRem

def striphtml(text):
    return re.sub('<.*?>', '', text)

def clean(html):
    """strip html and unquotehtml"""
    for tag in ['<br>', '<br />', '<p>']:
        html = html.replace(tag, ' ')
    html = COMMENT.sub('', html)
    return unquotehtml(htmlstripper.stripHTML(html,'UTF-8'))

def link(url, timeout=5, version=False):
    """save URL link to temp file, return html
        if it fails, retry after timeout=5 seconds; use input ua"""
    if version:
        NestOpener.version = version
    myOpener = NestOpener()
    try:
        page = myOpener.open(url)
    except (IOError, AttributeError):
        time.sleep(timeout)
        try:
            page = myOpener.open(url)            
        except (IOError, AttributeError):
            return False
    try:
        html = page.read()
    except Exception:
        time.sleep(timeout)
        try:
            html = page.read()
        except Exception:
            logger.exception('SCRAPPY: After waiting page could not be read.')
            return ""
    return reallyunicode(html)



def istyperight(doc):
    for (field, val) in doc.items():
        ## Some docs in sands have None in them (how?) so
        ## we need to clean them to re-add them.
        if val is None:
            doc.pop(field)
        if isinstance(val, list):
            while None in val:
                val.remove(None)

        if not is_right_type(field, val):
            logger.error("field %s and value %s were not right type", field, val)
            if isinstance(val, list):
                logger.error("BAD TYPE; DID NOT ADD DOCUMENT. Field '%s' had value %s, which is %s.", field, val, set(type(x) for x in val))
            else:
                logger.error("BAD TYPE; DID NOT ADD DOCUMENT. Field '%s' had value %s, which is %s.", field, val, type(val))
            return False

    return True

def is_right_type(fieldname, value):
    OurDateType = type(datetime.datetime.today())
    if fieldname in ['thingID', 'url', 'id'] or fieldname.startswith('_'): 
        return type(value) in (StringType, UnicodeType)
    if fieldname in ['indexed', 'modified']:
        return type(value) == OurDateType
    if fieldname in ['score']:
        return type(value) == FloatType

    righttypes = {'i_': (IntType,) ,
                  'f_': (FloatType,IntType) ,
                  's_': (StringType, UnicodeType) ,
                  'v_': (StringType, UnicodeType) ,
                  't_': (StringType, UnicodeType) ,
                  'n_': (StringType, UnicodeType) ,
                  'b_': (BooleanType,) ,
                  'd_': (OurDateType,) ,
                  'l_': (IntType, LongType) }
    rightfuncs = {'i_': int,
                  'f_': float,
                  'l_': long,
                  'b_': str2bool}

    prefix = fieldname[:2]
    if prefix not in righttypes:
        raise ValueError("Field called %s has an invalid prefix for sands." % fieldname, 'uknown doc ID')
    if type(value) is ListType:
        return bool(False not in [is_right_type(fieldname, x) for x in value])
    if type(value) in (StringType, UnicodeType) and prefix in rightfuncs:
        try:
            rightfuncs[prefix](value)
            ## What the HELL people
            if prefix == 'f_' and str(float(value)) in ['inf', '-inf', 'nan']:
                return False
            sys.stderr.write("Warning: string '%s' being added with prefix '%s'.\n" % (value, prefix))
            return True
        except ValueError:
            return False
    ## Finally, if the prefix is valid and it's not an array
    ## AND it's not a string that Solr will numericalize,
    ## then answer the obvious way: is it the right type?
    return type(value) in righttypes[prefix]

def remove_control_chars(s):
    return CONTROL_CHARS.sub('', s)

def is_valid_unicode_xml_char(character):
    '''
    test whether a unicode character can exist in an xml document,
    according to the characters specified in:

	Char ::= #x9 | #xA | #xD | [#x20-#xD7FF] | [#xE000-#xFFFD] | [#x10000-#x10FFFF]	/* any Unicode character, excluding the surrogate blocks, FFFE, and FFFF. */
    
    as defined in:
    http://www.w3.org/TR/2000/REC-xml-20001006#NT-Char

    raises TypeError `character` is not unicode
    '''

    if not isinstance(character, unicode):
        raise TypeError('character must be unicode')

#    if len(character) != 1:
#        raise ValueError('character must be a single character: %s' % character)

    if character in (u'\u0009', u'\u000A', u'\u000D'):
        return True

    if character < u'\u0020':
        return False

    if character > u'\uD7FF' and character < u'\uE000':
        return False

    if character > u'\uFFFD' and character < u'\U00010000':
        return False

    if character > u'\U0010FFFF':
        return False

    return True

def truncate_words(s, num, end_text='...'):
    """Truncates a string after a certain number of words. Takes an optional
    argument of what should be used to notify that the string has been
    truncated, defaults to ellipsis (...)"""
    s = reallyunicode(s)
    length = int(num)
    words = s.split()
    if len(words) > length:
        words = words[:length]
        if not words[-1].endswith(end_text):
            words.append(end_text)
    return u' '.join(words)
