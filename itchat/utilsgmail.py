import os
import sys
import io
from itertools import chain

import smtplib
import email
import email.Header
import imaplib

from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart


import email.header


def file2dict(fname):
    f = open(os.environ[fname],'r');
    emailcrd = {};
    ks = f.readline().strip().split(',');
    vs = f.readline().strip().split(',');
    for i in range(len(ks)):
        emailcrd[ks[i]] = vs[i];
    f.close();
    return emailcrd;

def search_string(uid_max, criteria):
    c = list(map(lambda t: (t[0], '"'+str(t[1])+'"'), \
                 criteria.items())) \
        + [('UID', '%d:*' % (uid_max+1))]
    return '(%s)' % ' '.join(chain(*c))
    # Produce search string in IMAP format:
    #   e.g. (FROM "me@gmail.com" SUBJECT "abcde" BODY "123456789" UID 9999:*)

def breakmultipart(msg):
    rv = [];
    for part in msg.get_payload():
        ptype = part.get_content_maintype();
        if(ptype != 'multipart'):
            rv.append(part);
        else:
            rv+=breakmultipart(part);
    return rv;

import random
import string 
def id_generator(size=8, chars=string.ascii_uppercase+string.digits):
    return ''.join(random.choice(chars) for _ in range(size));

import time
import datetime
dt =  datetime.datetime 
def ts_generator():
    return dt.strftime(dt.now(),'%y%m%d-%H%M%S%f');

def nm_generator():
    return '%s_%s'%(ts_generator(),id_generator());

def writemsg(emaildb,user,text,sufix=''):
    dbdirs = os.listdir(emaildb);
    for dbdir in dbdirs:
        dbname = emaildb+dbdir+'/'+nm_generator()+sufix;
        with io.open(dbname,'w',encoding='utf-8') as f:
            f.write(('wechat msg:'+user+'\n').decode('utf-8'));
            f.write(('|type:m|\n').decode('utf-8'));
            f.write(text);

def writedir(emaildb,user,flname,sufix=''):
    dbdirs = os.listdir(emaildb);
    for dbdir in dbdirs:
        dbname = emaildb+dbdir+'/'+nm_generator()+sufix;
        with open(dbname,'w') as f:
            f.write('wechat msg:'+user+'\n');
            f.write('|type:d|\n');
            f.write(flname);
    
class mygmail:
    def __init__(self, timesfile=''):
        self.emailcrd = file2dict('SESCRED');
        self.emaildb  = os.environ['EMAILDB'];
        self.downdir  = os.environ['DOWNDIR'];
        self.slt = 1;

    def send_txt(self,targets,subject,txtmsg):
        msg = MIMEText(txtmsg);
        msg['Subject'] = subject;
        msg['From']    = self.emailcrd['SENDER'];
        if(None==targets):
            targets = [self.emailcrd['RECEIVER']];
        msg['To'] = ', '.join(targets);
        server = smtplib.SMTP_SSL(self.emailcrd['SEND_HOST'],\
                                  self.emailcrd['SEND_PORT']);
        while(1):
            x = server.login(self.emailcrd['USER'],self.emailcrd['PASSWORD']);
            if('Accepted' in x[1]):
                break;
            print(x);
            time.sleep(self.slt);
            server = smtplib.SMTP_SSL(self.emailcrd['SEND_HOST'],\
                                      self.emailcrd['SEND_PORT']);

            
        server.sendmail(self.emailcrd['SENDER'],targets,msg.as_string());
        server.quit();

    def send_txtimg(self,targets,subject,txtmsg,filepath):
        msg = MIMEMultipart()
        msg['Subject'] = subject;
        msg['From'] = self.emailcrd['SENDER'];
        if(None==targets):
            targets = [self.emailcrd['RECEIVER']];
        msg['To'] = ', '.join(targets)
        msg.attach(MIMEText(txtmsg));
        
        with open(filepath, 'rb') as f:
            img = MIMEImage(f.read(),_subtype=filepath[filepath.rfind('.')+1:]);
        
        img.add_header('Content-Disposition',
                       'attachment',
                       filename=os.path.basename(filepath))
        msg.attach(img)

        server = smtplib.SMTP_SSL(self.emailcrd['SEND_HOST'],\
                                  self.emailcrd['SEND_PORT']);
        while(1):
            x = server.login(self.emailcrd['USER'],self.emailcrd['PASSWORD']);
            if('Accepted' in x[1]):
                break;
            print(x);
            time.sleep(self.slt);
            server = smtplib.SMTP_SSL(self.emailcrd['SEND_HOST'],\
                                      self.emailcrd['SEND_PORT']);

        server.sendmail(self.emailcrd['SENDER'],targets,msg.as_string());
        server.quit();

    def get_first_text_block(self,user,msg):
        type = msg.get_content_maintype()
        text = None;
        if type == 'multipart':
            parts = breakmultipart(msg);
            for part in parts:
                mtype = part.get_content_maintype();
                if('text' == mtype):
                    print('writing txt msg');
                    if(None==text):
                        text =  part.get_payload(decode=True).\
                                decode(part.get_content_charset());
                        writemsg(self.emaildb,user,text);
            #for a pure text message sent by gmail
            #part 0 is 'text', the content is the text itself
            #part 1 is 'text', the content is html element containing the text
                if('image' == mtype or 'application' == mtype):
                    print('writing dir info');
                    flname,encoding = email.Header.decode_header(part.get_filename())[0];
                    print(flname);
                    inddot = flname.rfind('.');
                    flpre = self.downdir+nm_generator();
                    filecontent = part.get_payload(decode=True);
                    open(flpre+flname,'wb').write(filecontent);
                    flname = flpre+nm_generator()+flname[inddot:];
                    open(flname,'wb').write(filecontent);
                    writedir(self.emaildb,user,flname);
        elif type == 'text':
            text =  msg.get_payload(decode=True).decode(msg.get_content_charset());
        if(None==text):
            rv = None;
        else:
            rv = text.encode('utf-8');
        #convert <type 'unicode'> to <type 'str'>



    def receive(self):
        server = imaplib.IMAP4_SSL(self.emailcrd['REC_HOST'],self.emailcrd['REC_PORT']);
        while(1):
            x = server.login(self.emailcrd['USER'],self.emailcrd['PASSWORD']);
            if('OK'==x[0]):
                break;
            print(x);
            time.sleep(self.slt);
            server = smtplib.SMTP_SSL(self.emailcrd['SEND_HOST'],\
                                      self.emailcrd['SEND_PORT']);

        server.select("INBOX");

        criteria = {
            'FROM':    'miaojilang@gmail.com',
            'SUBJECT': 'wechat'
        }

        uid_max = 0;
#Initialize `uid_max`. Any UID less than or equal to `uid_max` will be ignored subsequently
        rv,data = server.uid('search', None, search_string(uid_max, criteria))
        uids = [int(s) for s in data[0].split()]
        if uids:
            uid_max = max(uids)
        server.logout()
# Have to login/logout each time because that's the only way to get fresh results.
        while 1:
            server = imaplib.IMAP4_SSL(self.emailcrd['REC_HOST'],self.emailcrd['REC_PORT']);
            while(1):
                x = server.login(self.emailcrd['USER'],self.emailcrd['PASSWORD']);
                if('OK'==x[0]):
                    break;
                print(x);
                time.sleep(self.slt);
                server = smtplib.SMTP_SSL(self.emailcrd['SEND_HOST'],\
                                          self.emailcrd['SEND_PORT']);

            server.select("INBOX");
            rv,data = server.uid('search', None, search_string(uid_max, criteria));
            uids = [int(s) for s in data[0].split()]
            for uid in uids:
                # Have to check again because Gmail sometimes does not obey UID criterion.
                if uid > uid_max:
                    rv, data = server.uid('fetch', uid, '(RFC822)')  # fetch entire message
                    msg = email.message_from_string(data[0][1]);
                    uid_max = uid;
                    subj,encoding = email.Header.decode_header(msg['Subject'])[0];
                    ind1 = subj.rfind('(');
                    ind2 = subj.rfind(')');
                    username = subj[ind1+1:ind2].replace('#','@');
                    print('New message from ',username);
                    self.get_first_text_block(username,msg);

            
            server.logout();
            time.sleep(self.slt*5);



if __name__ == "__main__":
    g = mygmail()
    g.receive()
