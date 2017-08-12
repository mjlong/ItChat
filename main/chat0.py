import itchat
ses = itchat.new_instance();
ses.auto_login(enableCmdQR=1,hotReload=True, statusStorageDir='ses1jlmiao.pkl');

fg = ses.search_chatrooms(name="fbgrp")[0];
fg.send('successfully logged on athena.dialup.mit.edu');


