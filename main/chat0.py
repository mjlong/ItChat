import itchat
ses0 = itchat.new_instance();
ses0.auto_login(enableCmdQR=1,hotReload=True, statusStorageDir='ses1jlmiao.pkl');

fg = ses0.search_chatrooms(name="fbgrp")[0];
fg.send('successfully logged on athena.dialup.mit.edu');


