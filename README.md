#### 简单介绍     
本项目基于github.com/ddgth/cf2dns二次开发增加了更多功能与平台支持。    
功能上主要用于自动化将优选IP地址解析到您的域名记录中。    
支持CloudFlare、CloudFront、Gcore优选IPv4&IPv6地址    
支持宝塔面板、python3、GitHub-Actions三种方式部署。    
    
#### 演示图片    
 ![cf2dns.jpg](https://raw.githubusercontent.com/gacjie/cf2dns/main/cf2dns.jpg)   
        
#### 公告通知    
出于运维成本、长久稳定性等情况考虑。    
目前平台域名更换为WeTest.vip。    
请各位用户及时将插件更新到1.9版本以上。     
    
#### 接口支持    
CloudFlare官方优选(WeTest.vip)   更新频率15IP/15分钟   
CloudFlare官方优选(HostMonit.com)更新频率15IP/15分钟   
CloudFlare官方优选(345673.xyz)   更新频率15IP/15分钟    
CloudFront官方优选(WeTest.vip)   更新频率15IP/15分钟   
Gcore官方优选     (WeTest.vip)   更新频率15IP/15分钟   
        
#### 解析支持    
[华为云解析](https://support.huaweicloud.com/devg-apisign/api-sign-provide-aksk.html)   
[阿里云解析](https://help.aliyun.com/document_detail/53045.html?spm=a2c4g.11186623.2.11.2c6a2fbdh13O53)   
[腾讯云解析(DNSPOD)](https://console.cloud.tencent.com/cam/capi)   
         
#### 宝塔兼容性   
已测试支持以下版本    
aapanel7.0.7   
btpanel7.7.0    
btpanel9.0.0-lts    
         
#### 小广告
   
[【弘速云hosuyun.com】香港、美国高性能优质线路服务器，新用户首购五折特惠。](https://www.hosuyun.com/)  
[【宝塔bt.cn】宝塔产品特惠，linux专业版1年仅需￥699。](https://www.bt.cn/p/2PcEKn)    
[【腾讯云cloud.tencent.com】云产品1折特惠，2核2G4M仅需108元/年](https://curl.qcloud.com/zASK1SLm)     
[【阿里云aliyun.com】云产品爆款特惠，2核2G3M仅需82元/年](https://www.aliyun.com/minisite/goods?userCode=zqpad1gj)    
         
#### 价格计费    
插件免费提供授权码o1zrmHAF，可永久免费使用。    
[WeTest.vip付费服务说明](https://github.com/gacjie/cf2dns/wiki/WeTest付费服务说明)   
[WeTest.vip付费授权码购买](https://www.wetest.vip/dash/Account/register)   
[HostMonit.com付费授权码](https://shop.hostmonit.com/)   
[345673.xyz付费授权码](https://345673.xyz/)  
          
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
   
#### 2024年09月30日更新记录（V1.9）            
更新接口地址为WeTest.vip   
插件版增加对传入的字符串过滤空格、换行符   
   
#### 常见问题        
   
Q：为啥别人使用优选很快，我使用优选访问慢？      
A: 通常优选系统只会测用户端 - CDN节点的速度，但是节点也是要访问源站获取数据，源站与节点链接不稳定也会导致整体访问慢。   
A：建议增加缓存或有条件更换国际线路较好的源站服务器来优化链接速度。   
      
Q：为什么不支持反代优选？      
A：本项目是为了建站而开发，反代优选IP为扫描的第三方的服务器，存在不可控的安全隐患。   
A：目前已有因使用反代优选导致域名被注册机构禁用的先例。      
A：因此本项目未来也不会提供反代优选，除非您自行添加相关接口。       
         
Q：为什么不支持海外dns解析运营商？        
A：由于cf等cdn属于泛播，移动联通电信需要单独解析，才能实现三网优选。海外dns均不支持国内三网线路解析。      
A：如不方便使用国内云解析 可以访问 https://www.WeTest.vip 获取公共cname地址使用。       
     
Q：该插件安全吗？      
A：插件是基于cf2dns增加了宝塔可视化操作界面。并且代码全部公开在github上面，可先自行审查代码再决定是否安装。      
      
Q：为什么不做成其他面板的插件？      
A：由于cf2dns源代码是基于python3编写的，而宝塔面板的运行环境也是python3，所以可以很方便的写成插件，不需要考虑python3环境问题。       