#!/bin/bash
PATH=/www/server/panel/pyenv/bin:/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

#配置插件安装目录
install_path=/www/server/panel/plugin/cf2dns

#安装
Install()
{
	
	echo '正在安装...'
	#==================================================================
	#依赖安装开始
    btpip install -r $install_path/requirements.txt
	#依赖安装结束
	#==================================================================
	echo '================================================'
	#bt restart
}

#卸载
Uninstall()
{
	rm -rf $install_path
}

#操作判断
if [ "${1}" == 'install' ];then
	Install
elif [ "${1}" == 'uninstall' ];then
	Uninstall
else
	echo 'Error!';
fi
