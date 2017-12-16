import sys
import itchat
ses = itchat.new_instance();
ses.auto_login(hotReload=True, statusStorageDir=sys.argv[1]+'.pkl');
ses.run(fwemail=False);
