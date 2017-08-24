import os,logging, traceback, sys, threading
try:
    import Queue
except ImportError:
    import queue as Queue

from ..log import set_logging
from ..utils import test_connect,send_txt
from ..storage import templates

logger = logging.getLogger('itchat')

def load_register(core):
    core.auto_login       = auto_login
    core.configured_reply = configured_reply
    core.configured_send  = configured_send
    core.msg_register     = msg_register
    core.run              = run
    core.runsend          = runsend

def auto_login(self, hotReload=False, statusStorageDir='itchat.pkl',
        enableCmdQR=False, picDir=None, qrCallback=None,
        loginCallback=None, exitCallback=None):
    logger.info("Logging ...");
    if not test_connect():
        logger.info("You can't get access to internet or wechat domain, so exit.")
        sys.exit()
    self.useHotReload = hotReload
    self.hotReloadDir = statusStorageDir
    if hotReload:
        logger.info("Login status loading ... ");
        if self.load_login_status(statusStorageDir,
                loginCallback=loginCallback, exitCallback=exitCallback):
            logger.info("Login status loaded");
            return
        self.login(enableCmdQR=enableCmdQR, picDir=picDir, qrCallback=qrCallback,
            loginCallback=loginCallback, exitCallback=exitCallback)
        self.dump_login_status(statusStorageDir)
    else:
        self.login(enableCmdQR=enableCmdQR, picDir=picDir, qrCallback=qrCallback,
            loginCallback=loginCallback, exitCallback=exitCallback)

def msg2email(msg,senderType):
    pref="";
    if(2==senderType):
        pref+=(msg['ActualNickName']+':').encode('utf-8');
    if(msg['Type']=='Text'):
        send_txt(msg['User']['UserName'].replace('@','#'),\
                 msg['User']['NickName'],\
                 pref+msg['Text'].encode('utf-8'));
    
def configured_reply(self):
    ''' determine the type of message and reply if its method is defined
        however, I use a strange way to determine whether a msg is from massive platform
        I haven't found a better solution here
        The main problem I'm worrying about is the mismatching of new friends added on phone
        If you have any good idea, pleeeease report an issue. I will be more than grateful.
    '''
    try:
        msg = self.msgList.get(timeout=1);
    except Queue.Empty:
        pass
    else:
        replyFn = None;
        if isinstance(msg['User'], templates.User):
            logger.info('new message from '+msg['User']['UserName']);
            msg2email(msg,1);
            replyFn = self.functionDict['FriendChat'].get(msg['Type']);
        elif isinstance(msg['User'], templates.MassivePlatform):
            replyFn = self.functionDict['MpChat'].get(msg['Type'])
        elif isinstance(msg['User'], templates.Chatroom):
            logger.info('new message from '+msg['User']['UserName']);
            msg2email(msg,2);
            replyFn = self.functionDict['GroupChat'].get(msg['Type'])
        if replyFn is None:
            r = None
        else:
            try:
                r = replyFn(msg)
                if r is not None:
                    self.send(r, msg.get('FromUserName'))
            except:
                logger.warning(traceback.format_exc())

def msg_register(self, msgType, isFriendChat=False, isGroupChat=False, isMpChat=False):
    ''' a decorator constructor
        return a specific decorator based on information given '''
    if not (isinstance(msgType, list) or isinstance(msgType, tuple)):
        msgType = [msgType]
    def _msg_register(fn):
        for _msgType in msgType:
            if isFriendChat:
                self.functionDict['FriendChat'][_msgType] = fn
            if isGroupChat:
                self.functionDict['GroupChat'][_msgType] = fn
            if isMpChat:
                self.functionDict['MpChat'][_msgType] = fn
            if not any((isFriendChat, isGroupChat, isMpChat)):
                self.functionDict['FriendChat'][_msgType] = fn
        return fn
    return _msg_register

def run(self, debug=False, blockThread=True):
    logger.info('Start auto forwarding.')
    if debug:
        set_logging(loggingLevel=logging.DEBUG)
    def reply_fn():
        try:
            while self.alive:
                self.configured_reply()
        except KeyboardInterrupt:
            if self.useHotReload:
                self.dump_login_status()
            self.alive = False
            logger.debug('itchat received an ^C and exit.')
            logger.info('Bye~')
    if blockThread:
        reply_fn()
    else:
        replyThread = threading.Thread(target=reply_fn)
        replyThread.setDaemon(True)
        replyThread.start()

def runsend(self):
    logger.info('Start auto sending.')
    def reply_fn():
        try:
            while self.alive:
                self.configured_send()
        except KeyboardInterrupt:
            if self.useHotReload:
                self.dump_login_status()
            self.alive = False
            logger.debug('itchat received an ^C and exit.')
            logger.info('Bye~')
    reply_fn()

import email
def configured_send(self):
    emaildbpath = os.environ['EMAILDB'];
    messagefiles = os.listdir(emaildbpath);
    for filename in messagefiles:
        realname = emaildbpath+filename;
        print('processing message from'+realname);
        f = open(realname,'r');
        emsg = email.message_from_file(f);
        f.close();
        ind = emsg['To'].find('_wechat@');
        if(-1!=ind):
            text = [];
            if emsg.is_multipart():
                for p in emsg.get_payload():
                    text.append(p.get_payload(decode=True).decode(p.get_content_charset()));
            else:
                text.append(emsg.get_payload(decode=True).decode(emsg.get_content_charset()));
            text = ''.join(text[0]);
            print(text);
            print(text.encode('utf-8'));

            userid = (emsg['To'].replace('#','@'))[:ind];
            print('userName = '+userid);

            user = None;
            if('@'==userid[0]):
                if('@'!=userid[1]):
                    user = self.search_friends(userName=userid);
                else:
                    user = self.search_chatrooms(userName=userid);
            if(None!=user):
                user.send(text);
            else:
              text = text.strip();
              if(-1!= emsg['To'].find('search_friends_wechat@')):
                users = self.search_friends(nickName=text.strip());
                for u in users:
                  send_txt(u['UserName'].replace('@','#'),u['NickName'], 'friend found with alias='+text); 
                if(0==len(users)):
                  send_txt('search_friends','friends helper', 'no friend found with alias='+text);  
              if(-1!= emsg['To'].find('chatrooms_wechat@')):
                rooms = self.search_chatrooms(name=text);
                for r in rooms:
                  send_txt(r['UserName'].replace('@','#'),r['NickName'], 'chatroom found with alias='+text); 
                if(0==len(rooms)):
                  send_txt('search_chatrooms','chatrooms helper', 'no chatroom found with alias='+text);  
 
            os.remove(realname);

     
        
