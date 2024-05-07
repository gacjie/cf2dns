#### 简单介绍     
本项目基于github.com/ddgth/cf2dns二次开发增加了更多功能与平台支持。    
功能上主要用于自动化将优选IP地址解析到您的域名记录中。    
支持CloudFlare、CloudFront、Gcore优选IPv4&IPv6地址    
支持宝塔面板、python3、GitHub-Actions三种方式部署。    
支持GacJieMonitor(monitor.gacjie.cn)、HostMonit(stock.hostmonit.com)两个平台获取数据。
   
#### 云服务监测平台(https://monitor.gacjie.cn)     
由于近期移动抽风屏蔽eu.org域名，影响监测脚本提交数据，故我把域名全换掉了。     
不再使用eu.org域名，请大家及时更换新的地址链接。    
    
#### 演示图片    
 ![cf2dns.jpg](https://raw.githubusercontent.com/gacjie/cf2dns/main/cf2dns.jpg)   
         
#### 功能说明    
支持从GacJieMonitor(monitor.gacjie.cn)获取CloudFlare、CloudFront、Gcore优选IP地址   
支持从HostMonit(stock.hostmonit.com)获取CloudFlare优选IP地址          
支持从345673.xyz(345673.xyz)获取CloudFlare优选IP地址   
支持将优选IP解析至DNSPOD        
支持将优选IP解析至阿里云解析          
支持将优选IP解析至华为云解析          
支持查询授权余额          
支持ipv4&ipv6同时获取并解析                 
支持宝塔部署cf2dns插件    
支持python3部署运行cf2dns_global    
支持GitHub-Actions-运行cf2dns_actions    
         
#### 小广告
[【宝塔】送你10850元礼包](https://www.bt.cn/?invite_code=M19yaHFycXY=)    
[【腾讯云】云产品1折特惠专区](https://curl.qcloud.com/zASK1SLm)     
[【阿里云】云产品爆款特惠](https://www.aliyun.com/minisite/goods?userCode=zqpad1gj)    
         
#### 价格计费    
插件免费提供授权码o1zrmHAF，可永久免费使用。    
[GacJieMonitor](https://github.com/gacjie/cf2dns/wiki/GacJieMonitor付费KEY价格)   
[HostMonit小店](https://shop.hostmonit.com/)   
[345673.xyz](https://345673.xyz/)  
          
### 注意事项     
宝塔安装时请关闭宝塔系统加固插件，会终止安装脚本的执行。     
脚本只会更新电信、移动、联通三网线路的IP，因此还需要将回退源设置到默认线路上。      
使用插件前请确保您的网站域名使用cname或saas方式接入，并且域名解析在dnspod、华为云、阿里云。       
     
#### 使用说明   
[宝塔安装cf2dns插件](https://github.com/gacjie/cf2dns/wiki/宝塔安装cf2dns插件)   
[python3部署运行cf2dns_global](https://github.com/gacjie/cf2dns/wiki/python3部署运行cf2dns_global)  
[GitHub Actions 运行cf2dns_actions](https://github.com/gacjie/cf2dns/wiki/GitHub-Actions-运行cf2dns_actions)  
        
#### 数据备份     
config.json是配置数据    
domains.json是域名数据    
cf2dns插件、cf2dns_global、cf2dns_actions均支持。    
配置完后可以直接备份这俩数据文件，后续需要迁移可直接上传。     
   
#### 2024年05月07日更新记录          
修复宝塔cf2dns插件无法保存地域的bug
增加345673.xyz服务商接口
由于没有什么大的更新版本
插件还是使用1.5版本

#### 常见问题        
      
Q：为什么不支持海外dns解析运营商？     
A：由于cf等cdn属于泛播，移动联通电信需要单独解析，才能实现三网优选。海外dns均不支持国内三网线路解析。      
如不方便使用国内云解析 可以访问 https://monitor.gacjie.cn/page/cname/index.html 获取公共cname地址使用。       
     
Q：使用该插件更新IP后，导致网站全都打不开了？      
A：使用优选IP的前提是，cdn使用cname(别名)方式接入，本插件只是将获取的优选IP解析到您的域名上去，网站打不开是因为你的CDN配置问题。        
     
Q：该插件安全吗？      
A：插件是基于cf2dns增加了宝塔可视化操作界面。并且代码全部公开在github上面，可先自行审查代码再决定是否安装。      
      
Q：为什么不做成其他面板的插件？      
A：由于cf2dns源代码是基于python3编写的，而宝塔面板的运行环境也是python3，所以可以很方便的写成插件，不需要考虑python3环境问题。       