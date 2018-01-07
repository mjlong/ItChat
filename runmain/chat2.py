import sys
import itchat
ses = itchat.new_instance();
ses.auto_login(hotReload=True, statusStorageDir=sys.argv[1]+'.pkl');
ses.runsend(sys.argv[1]+"/",timesfile='timeparafile',drysend=True,eastereggfile='EEggs');
