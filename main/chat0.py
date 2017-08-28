import itchat
ses = itchat.new_instance();
ses.auto_login(hotReload=True, statusStorageDir='ses1jlmiao.pkl');

fg = ses.search_chatrooms(name="Testgroup1")[0];
fg.send('successfully logged on desktop');


