import time,os,logging, traceback, sys, threading,requests
import numpy as np
try:
    import Queue
except ImportError:
    import queue as Queue

from ..log import set_logging
from ..utils import test_connect,send_txt,send_img,readgg
from ..storage import templates
from .. import utilsgmail

logger = logging.getLogger('itchat')
sufgroup = '_groupfor'; 
#append to emaildb filename to distinguish messages I want to send and messages I want to for(ward) among groups
#email dbname follows the pattern datetime_len(8)letter therefore the '_groupfor' is guaranteed to not appear

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

def strexpand(x):
    l = len(x)+1;
    a = int(l*0.2);
    #i = np.random.choice(l,a,replace=False) + np.arange(a);
    #for j in i:
    #    x = x[:j] + ' ' + x[j:];
    sepas = [':', ',', ';','.','!','?','(',')'];
    for sepa in sepas:
        ind = x.find(sepa);
        if(-1==ind):
            x = x+' ';
        else:
            x = x[:ind] + ' ' + x[ind:];

    return x;

def msg2email(msg,senderType,myname='[]',fwemail=True):
    rvtext = None;
    if(not 'UserName' in msg['User'].keys()):
        return None;
    mtype = msg['Type'];
    logger.info('new message of type '+mtype+' from '+msg['User']['UserName']);
    pref="";
    if(2==senderType):
        pref+=(msg['ActualNickName']+':').encode('utf-8');
    if('Text'==mtype):
        rvtext = pref+msg['Text'].encode('utf-8');
        if(fwemail):
            send_txt(msg['User']['UserName'],\
                     myname+msg['User']['NickName'],\
                     rvtext);
        if(str is type(rvtext)):
            rvtext = rvtext.decode('utf-8');
        rvtext = [strexpand(rvtext)];
    if(mtype in ('Picture','Attachment','Recording','Video')):
        fileDir = os.environ['DOWNDIR']+msg['FileName'];
        logger.info('downloading file ...');
        msg['Text'](fileDir);
        if(fwemail):
            send_img(msg['User']['UserName'],\
                     myname+msg['User']['NickName'],\
                     pref,fileDir);
        tmptxt = filedir2msg(fileDir);
        if(unicode is type(tmptxt)):
            tmptxt=tmptxt.encode('utf-8');
            print('rare event happens, filename contains unicode');
        rvtext = [tmptxt];

    if('Card'==mtype):
        rvtext = []
        rtxt = pref+('Recommended Contact:'+msg['Text']['NickName']).encode('utf-8');
        if(fwemail):
            send_txt(msg['User']['UserName'],\
                     myname+msg['User']['NickName'],\
                     rtxt);
        if(str is type(rtxt)):
            rtxt = rtxt.decode('utf-8');
        rvtext.append(rtxt);
        uid = msg['RecommendInfo']['UserName'].encode('utf-8');
        print('uid',uid);
        url = msg['Content'].encode('utf-8');
        ind = url.find("bigheadimgurl=\"");
        url = url[ind+15:];
        ind = url.find("\"");
        url = url[:ind];
        print('url',url);
        if(len(url)>1):
            fileDir = os.environ['DOWNDIR']+uid+'.png';
            open(fileDir,'wb').write(requests.get(url,allow_redirects=True).content);
            if(fwemail):
                send_img(msg['User']['UserName'],\
                         myname+msg['User']['NickName'],\
                         "the profile is",fileDir);
            rvtext.append(filedir2msg(fileDir));

    if(mtype == 'Sharing'):
        ct = msg['Content'].encode('utf-8');
        i1 = ct.find('<title>')+7;
        i2 = ct.find('</title>');
        tt = ct[i1:i2];
        i1 = ct.find('<des>')+5;
        i2 = ct.find('</des>');
        ds = ct[i1:i2];
        i1 = ct.find('<url>')+5;
        i2 = ct.find('</url>');
        ul = ct[i1:i2];

        rvtext = pref+tt+'\n'+ds+'\n'+ul;
        if(fwemail):
            send_txt(msg['User']['UserName'],\
                     myname+msg['User']['NickName'],\
                     rvtext);
        if(str is type(rvtext)):
            rvtext = rvtext.decode('utf-8');
        rvtext = [rvtext];

    return rvtext;

def isTextMsg(msg):
    return not (('@fil@/' in msg)  or  ('@img@/' in msg) or ('@vid@/' in msg)  );

def configured_reply(self,emaildir):
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
            msg2email(msg,1,self.myname,self.fwemail);
            replyFn = self.functionDict['FriendChat'].get(msg['Type']);
        elif isinstance(msg['User'], templates.MassivePlatform):
            msg2email(msg,3,self.myname,self.fwemail);
            replyFn = self.functionDict['MpChat'].get(msg['Type'])
        elif isinstance(msg['User'], templates.Chatroom):
            rvtext = msg2email(msg,2,self.myname,self.fwemail);
            if(None!=rvtext and 2<len(rvtext)):
                rvtext = rvtext[:2];
            print(rvtext);
            if(None!=rvtext):
                for ttt in rvtext:
                  if(None!=ttt):
                    if(unicode is type(ttt)):
                        print(ttt.encode('utf-8'));
                    else:
                        print(ttt);
            myid = self.memberList[0]['UserName'];
            gid = msg['User']['UserName'];
            if(myid!=msg['ActualUserName'] and gid in self.g2ind.keys()):
                print('forwarding....');
                ind = self.g2ind[gid];
                for g in self.ggids[ind]:
                    print('f to',g);
                    if(g!=gid):
                        time.sleep(1+np.random.rand());
                        for rtxt in rvtext:
                            print(rtxt)
                            print(type(rtxt))
                            print('send--->'+rtxt.encode('utf-8'));

                            if(str is type(rtxt)): #rtxt is str (thus file path and username is not included), 
                                utilsgmail.writemsg(emaildir,g,             \
                                                    utilsgmail.dt.strftime( \
                                                        utilsgmail.dt.now(),'[%Y/%m/%d-%H:%M:%S]') \
                                                    +msg['ActualNickName']+':',sufgroup);
                                #self.send_msg(msg['ActualNickName']+':',toUserName=g);
                                if('.gif'==rtxt[-4:]):
                                    utilsgmail.writemsg(emaildir,g,'sticker unavailable'.decode('utf-8'),sufgroup); #make type str be type unicode
                                    #self.send('sticker unavailable', toUserName=g);

                                utilsgmail.writedir(emaildir,g,rtxt[5:],sufgroup);
                            else:
                                print('writing text msg.........',rtxt);
                                temp = utilsgmail.dt.strftime(utilsgmail.dt.now(),'[%Y/%m/%d-%H:%M:%S]')+rtxt;
                                print('the msg is',temp);
                                utilsgmail.writemsg(emaildir,g,temp,sufgroup );
                            #self.send(rtxt, toUserName=g);
        
            replyFn = self.functionDict['GroupChat'].get(msg['Type']);
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

def run(self, debug=False, blockThread=True,gname='groupgroup',mydir='',fwemail=True):
    self.myname = '[%s]'%self.memberList[0]['NickName'];
    self.fwemail = fwemail;
    logger.info('Start auto forwarding.')
    if debug:
        set_logging(loggingLevel=logging.DEBUG)
    def reply_fn():
        try:
            while self.alive:

                ggs = readgg(gname);
                self.ggids = [];
                self.g2ind = dict();

                ig = 0;
                for gg in ggs:
                    gids = [];
                    for g in gg:
                        gid = self.search_chatrooms(name=g);
                        if([]==gid):
                            print('Warning! '+g+' not found');
                        else:
                            gidn = gid[0]['UserName'];
                            self.g2ind[gidn] = ig;
                            gids.append(gidn);
                    self.ggids.append(gids);
                    print(gids)
                    ig+=1;
            
                self.configured_reply(os.environ['EMAILDB']+mydir)
                time.sleep(1.5+np.random.rand());
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

def runsend(self,mydir="",timesfile='',drysend=False):
    logger.info('Start auto sending.')
    self.myname = '[%s]'%self.memberList[0]['NickName'];
    def reply_fn():
        try:
            t0 = time.clock();
            dictUserMsgs = dict(); #dict in the form: {u1:[tmsg+tmsg+..., dmsg, tmsg+..,dmsg,dmsg...],u2:[...]}
            dictUserType = dict(); #dict in the form: {u1:lasttype, u2:lastype,}
            dictUserUids = dict(); #dict in the form: {uid:user,uid:user}

            while self.alive:
                #self.configured_send(mydir,waitperiod);

                emaildbpath = os.environ['EMAILDB']+mydir;
                messagefiles = os.listdir(emaildbpath);
                messagefiles.sort();   #order matters especially in the archive forward mode, 
                                       #here sort string thus sort by file write name due to the file name generator in utilsgmail
                if([]!=messagefiles):
                    print('files to process:',messagefiles);

                if(''!=timesfile):
                    with open(timesfile) as f:
                        timeparas = f.readlines();
                    waitperiod = float(timeparas[0][:-1]); 
                    tsend_mu   = float(timeparas[1][:-1]); 
                    tsend_sig  = float(timeparas[2][:-1]);                   
                else:
                    waitperiod = 2; 
                    tsend_mu   = 5; 
                    tsend_sig  = 4;

                for filename in messagefiles:
                    isForGroup = sufgroup in filename;
                    realname = emaildbpath+filename;
                    userid,user,text,mtype = self.configured_send(realname);
                    os.remove(realname);
                    time.sleep(tsend_mu+np.abs(np.random.randn())*tsend_sig);
                    if(None!=user):
                        if(isForGroup):
                            if(userid in dictUserUids.keys()):
                                if('m'==mtype):
                                    if('m'== dictUserType[userid]): # last msg is also text msg, append to the last message of the user
                                        dictUserMsgs[userid][-1]+='\n......\n'+text;
                                    else:                    # last msg is file msg, append as new message of the user
                                        dictUserMsgs[userid].append(text); 
                                    dictUserType[userid]='m';
                                else:                        # this msg is file msg, append as new message of the user
                                    dictUserMsgs[userid].append(text);
                                    dictUserType[userid]='d';
                            else:
                                dictUserUids[userid] = user;
                                dictUserType[userid] = mtype;
                                dictUserMsgs[userid] = [text];
    
                        else:
                            user.send(text);
                            send_txt('auto confrim', self.myname+'msg helper', \
                                                    (text+'\n has been sent to \n'+user['NickName']).encode('utf-8'));
                            time.sleep(tsend_mu+np.abs(np.random.randn())*tsend_sig);

                t1 = time.clock();
                if(not drysend):
                    confirmMsg =['auto confirm','\n has been sent to\n'];
                else:
                    confirmMsg =['For mannual forward','\n should have been sent to\n'];
                if((t1-t0)*1000>waitperiod):
                    print('.....%.1f s passed........'%((time.clock()-t0)*1000));
                    for userid in dictUserUids.keys():
                        user = dictUserUids[userid];
                        for text in dictUserMsgs[userid]:
                            if(not drysend):
                                user.send(text);
                            print('msg sent',(text+confirmMsg[1]+user['NickName']).encode('utf-8'));
                            send_txt(confirmMsg[0], self.myname+'msg helper', \
                                     (text+confirmMsg[1]+user['NickName']).encode('utf-8'));
                            time.sleep(tsend_mu+np.abs(np.random.randn())*tsend_sig);
                        time.sleep(    tsend_mu+np.abs(np.random.randn())*tsend_sig);
                    
                    t0 = time.clock();
                    dictUserMsgs = dict(); 
                    dictUserType = dict(); 
                    dictUserUids = dict(); 
                time.sleep(tsend_mu+np.abs(np.random.randn())*tsend_sig);               

        except KeyboardInterrupt:
            if self.useHotReload:
                self.dump_login_status()
            self.alive = False
            logger.debug('itchat received an ^C and exit.')
            logger.info('Bye~')
    reply_fn()

def filedir2msg(fileDir):
    dot = fileDir.rfind('.');
    ftype = fileDir[dot+1:];
    prefix = '@fil@';
    if('png'==ftype or 'jpg'==ftype or 'gif'==ftype):
        prefix = '@img@';
    if('mp4'==ftype):
        prefix = '@vid@';
    return prefix+fileDir;

import io
def configured_send(self,realname):
        print('processing message from'+realname);
        f = io.open(realname,'r',encoding='utf-8');
        emsg = f.read().encode('utf-8');
        f.close();
        print('raw msg:'+emsg);
        ind = emsg.find('wechat msg:');
        if(-1!=ind):
            emsg = emsg[ind+11:];
            ind1 = emsg.find('\n');
            userid = emsg[:ind1];
            emsg = emsg[ind1+1:];

            ind1 = emsg.find('|type:');
            mtype = emsg[ind1+6];
            emsg  = emsg[ind1+9:];

            text = None;
            if('m'==mtype):
                text = emsg;
            if('d'==mtype): 
                text = filedir2msg(emsg);
            if(str is type(text)):
                text = text.decode('utf-8');


            print('userName = '+userid);

            user = None;
            if('@'==userid[0]):
                if('@'!=userid[1]):
                    user = self.search_friends(userName=userid);
                else:
                    user = self.search_chatrooms(userName=userid);
            return userid,user,text,mtype
                
#            if(None!=user):
#                print('sending...',text);
#                user.send(text);
#                send_txt('auto confirm', self.myname+'msg helper', (text+'\n has been sent to\n'+user['NickName']).encode('utf-8'));
 



import email
def configured_send_procmail(self):
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

     
        
