#### 简单介绍
本项目为cf2dns宝塔插件版。
为了方便部署，因此将原项目github.com/ddgth/cf2dns做成了宝塔插件。
功能上主要用于将CloudFlare优选IP地址解析到您的域名记录中。
后续降逐渐支持CloudFront Gcore等其他CDN服务。

#### 云服务监测平台(https://monitor.gacjie.cn)
由于近期移动抽风屏蔽eu.org域名，影响监测脚本提交数据，故我把域名全换掉了。
不再使用eu.org域名，请大家及时更换新的地址链接。

#### 演示图片    
 ![cf2dns.jpg](https://raw.githubusercontent.com/gacjie/cf2dns/main/cf2dns.jpg)   
 
#### 功能说明    
支持从GacJieMonitor(monitor.gacjie.cn)获取CloudFlare优选IP地址    
支持从HostMonit(stock.hostmonit.com)获取CloudFlare优选IP地址    
支持将优选IP解析至DNSPOD     
支持将优选IP解析至阿里云解析     
支持将优选IP解析至华为云解析     
支持查询授权余额     

#### 优选数据来源
目前兼容支持cf2dns原作者的接口(https://stock.hostmonit.com/CloudFlareYes)以及本人的云服务监测平台(https://monitor.gacjie.cn)。
GacJieMonitor：严格的筛选规则，脚本每段时间提交的IP较少，每个key获取IP会缓存15分钟（缓存期间请求不记次数）。
HostMonit：为获取更多IP，筛选规则宽松，用于解决假墙问题，但会分配欧州节点，接口没有缓存限制。

#### 价格计费    
插件免费提供授权码o1zrmHAF，可永久免费使用。    
短期内还不会去写授权购买页面，开发重点暂时以脚本优化支持其他cdn为主。    
插件首页有Q群号，如需付费授权购买，可加群后联系群主。    
免费付费区别在于，由于每个授权码每次获取IP会缓存15分钟。    
因此免费授权码给的IP是大家共享一组的。     
付费授权码，则是独享一组IP。     
请求缓存数据不会计费。     

#### 使用说明  
将本项目ZIP包下载到电脑，打开面板-软件商店-第三方应用-导入安装即可

#### 技术交流      
     
技术教程：www.baota.me     
QQ交流群：699927761      
TG交流群：t.me/btfans    
 
