import os
import smtplib
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart

def file2dict(fname):
    f = open(os.environ[fname],'r');
    emailcrd = {};
    ks = f.readline().strip().split(',');
    vs = f.readline().strip().split(',');
    for i in range(len(ks)):
        emailcrd[ks[i]] = vs[i];
    f.close();
    return emailcrd;

class mygmail:
    def __init__(self):
        self.emailcrd = file2dict('SESCRED');

    def send_txt(self,targets,subject,txtmsg):
        msg = MIMEText(txtmsg);
        msg['Subject'] = subject;
        msg['From']    = self.emailcrd['SENDER'];
        if(None==targets):
            targets = [self.emailcrd['RECEIVER']];
        msg['To'] = ', '.join(targets);
        server = smtplib.SMTP_SSL(self.emailcrd['SEND_HOST'],\
                                  self.emailcrd['SEND_PORT']);
        server.login(self.emailcrd['USER'],self.emailcrd['PASSWORD']);
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
        server.login(self.emailcrd['USER'],self.emailcrd['PASSWORD']);
        server.sendmail(self.emailcrd['SENDER'],targets,msg.as_string());
        server.quit();
