import io, re, os, sys, subprocess, copy, traceback, logging
from os import path

try:
    from HTMLParser import HTMLParser
except ImportError:
    from html.parser import HTMLParser

import requests

from . import config

logger = logging.getLogger('itchat')

emojiRegex = re.compile(r'<span class="emoji emoji(.{1,10})"></span>')
htmlParser = HTMLParser()
try:
    b = u'\u2588'
    sys.stdout.write(b + '\r')
    sys.stdout.flush()
except UnicodeEncodeError:
    BLOCK = 'MM'
else:
    BLOCK = b
friendInfoTemplate = {}
for k in ('UserName', 'City', 'DisplayName', 'PYQuanPin', 'RemarkPYInitial', 'Province',
        'KeyWord', 'RemarkName', 'PYInitial', 'EncryChatRoomId', 'Alias', 'Signature', 
        'NickName', 'RemarkPYQuanPin', 'HeadImgUrl'):
    friendInfoTemplate[k] = ''
for k in ('UniFriend', 'Sex', 'AppAccountFlag', 'VerifyFlag', 'ChatRoomId', 'HideInputBarFlag',
        'AttrStatus', 'SnsFlag', 'MemberCount', 'OwnerUin', 'ContactFlag', 'Uin',
        'StarFriend', 'Statues'):
    friendInfoTemplate[k] = 0
friendInfoTemplate['MemberList'] = []

# read grouped groups
def readgg(fname):
    f = io.open(fname,'r',encoding='utf-8');
    nns = [];
    temp = None;
    for l in f:
        line = (l.encode('utf-8').strip()).decode('utf-8');
        if(u'<<<<<<'==line):
            temp = [];
        else:
            if(u'>>>>>>'==line):
                nns.append(temp);
            else:
                temp.append(line);
    f.close();
    return nns;

# read archived groups
def readag(fname):
    f = io.open(fname,'r',encoding='utf-8');
    nns = [];
    for l in f:
        line = (l.encode('utf-8').strip()).decode('utf-8');
        nns.append(line);
    f.close();
    return nns;

def clear_screen():
    os.system('cls' if config.OS == 'Windows' else 'clear')

def emoji_formatter(d, k):
    ''' _emoji_deebugger is for bugs about emoji match caused by wechat backstage
    like :face with tears of joy: will be replaced with :cat face with tears of joy:
    '''
    def _emoji_debugger(d, k):
        s = d[k].replace('<span class="emoji emoji1f450"></span',
            '<span class="emoji emoji1f450"></span>') # fix missing bug
        def __fix_miss_match(m):
            return '<span class="emoji emoji%s"></span>' % ({
                '1f63c': '1f601', '1f639': '1f602', '1f63a': '1f603',
                '1f4ab': '1f616', '1f64d': '1f614', '1f63b': '1f60d',
                '1f63d': '1f618', '1f64e': '1f621', '1f63f': '1f622',
                }.get(m.group(1), m.group(1)))
        return emojiRegex.sub(__fix_miss_match, s)
    def _emoji_formatter(m):
        s = m.group(1)
        if len(s) == 6:
            return ('\\U%s\\U%s'%(s[:2].rjust(8, '0'), s[2:].rjust(8, '0'))
                ).encode('utf8').decode('unicode-escape', 'replace')
        elif len(s) == 10:
            return ('\\U%s\\U%s'%(s[:5].rjust(8, '0'), s[5:].rjust(8, '0'))
                ).encode('utf8').decode('unicode-escape', 'replace')
        else:
            return ('\\U%s'%m.group(1).rjust(8, '0')
                ).encode('utf8').decode('unicode-escape', 'replace')
    d[k] = _emoji_debugger(d, k)
    d[k] = emojiRegex.sub(_emoji_formatter, d[k])

def msg_formatter(d, k):
    emoji_formatter(d, k)
    d[k] = d[k].replace('<br/>', '\n')
    d[k]  = htmlParser.unescape(d[k])

def check_file(fileDir):
    try:
        with open(fileDir):
            pass
        return True
    except:
        return False

import utilsgmail
def send_txt(senderid,sendername,message):
    g = utilsgmail.mygmail();
    g.send_txt(None,\
               'WeChat'+sendername+' sent a message ('+senderid+')', \
               message);

def send_img(senderid,sendername,message,fileDir):
    g = utilsgmail.mygmail();
    g.send_txtimg(None,\
                  'WeChat'+sendername+' sent a message ('+senderid+')', \
                  message, fileDir);


def send_qr(fileDir):
    g = utilsgmail.mygmail();
    g.send_txtimg(None,'WeChat Login',"Scan the attached QR code to login wechat",fileDir);
    
def print_qr(fileDir):
    if config.OS == 'Darwin':
        subprocess.call(['open', fileDir])
    elif config.OS == 'Linux':
        try:
            __IPYTHON__
        except NameError:
            #"Not in IPython"
            logger.info('please scan '+fileDir+' to login');
            #subprocess.call(['xdg-open', fileDir])
            send_qr(fileDir);
        else:
            logger.info('...xdg-open unavailable,'+ \
                        'please open file '+ \
                        path.abspath(path.dirname(fileDir))+'/'+fileDir\
                        +' to scan')
    else:
        os.startfile(fileDir)

def print_cmd_qr(qrText, white=BLOCK, black='  ', enableCmdQR=True):
    blockCount = int(enableCmdQR)
    if abs(blockCount) == 0:
        blockCount = 1
    white *= abs(blockCount)
    if blockCount < 0:
        white, black = black, white
    sys.stdout.write(' '*50 + '\r')
    sys.stdout.flush()
    qr = qrText.replace('0', white).replace('1', black)
    sys.stdout.write(qr)
    sys.stdout.flush()

def struct_friend_info(knownInfo):
    member = copy.deepcopy(friendInfoTemplate)
    for k, v in copy.deepcopy(knownInfo).items(): member[k] = v
    return member

def search_dict_list(l, key, value):
    ''' Search a list of dict
        * return dict with specific value & key '''
    for i in l:
        if i.get(key) == value:
            return i

def print_line(msg, oneLine = False):
    if oneLine:
        sys.stdout.write(' '*40 + '\r')
        sys.stdout.flush()
    else:
        sys.stdout.write('\n')
    sys.stdout.write(msg.encode(sys.stdin.encoding or 'utf8', 'replace'
        ).decode(sys.stdin.encoding or 'utf8', 'replace'))
    sys.stdout.flush()

def test_connect(retryTime=5):
    for i in range(retryTime):
        try:
            r = requests.get(config.BASE_URL)
            return True
        except:
            if i == retryTime - 1:
                logger.error(traceback.format_exc())
                return False

def contact_deep_copy(core, contact):
    with core.storageClass.updateLock:
        return copy.deepcopy(contact)

def get_image_postfix(data):
    data = data[:20]
    if b'GIF' in data:
        return 'gif'
    elif b'PNG' in data:
        return 'png'
    elif b'JFIF' in data:
        return 'jpg'
    return ''

def update_info_dict(oldInfoDict, newInfoDict):
    ''' only normal values will be updated here
        because newInfoDict is normal dict, so it's not necessary to consider templates
    '''
    for k, v in newInfoDict.items():
        if any((isinstance(v, t) for t in (tuple, list, dict))):
            pass # these values will be updated somewhere else
        elif oldInfoDict.get(k) is None or v not in (None, '', '0', 0):
            oldInfoDict[k] = v
