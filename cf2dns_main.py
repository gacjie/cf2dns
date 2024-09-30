#!/usr/bin/python
# coding: utf-8
#+--------------------------------------------------------------------
#|   CF2DNS OF BTPANEL 
#|   AUTH GACJIE
#+--------------------------------------------------------------------
import sys,os,json,requests,time,base64,shutil
#设置运行目录
os.chdir("/www/server/panel")

#添加包引用位置并引用公共包
sys.path.append("class/")
import public

class cf2dns_main:
    __plugin_path = "/www/server/panel/plugin/cf2dns/"
    __config = None
    __config_path = __plugin_path + "config.json"
    __domians_path = __plugin_path + "domains.json"
    __provider_path = __plugin_path + "provider.json"
    #构造方法
    def  __init__(self):
        pass

    #从获取解析配置信息
    def get_home_info(self, args):
        data =  json.loads(public.readFile(self.__config_path))
        return self.__response_json(data,200,'获取数据成功')
    #从设置解析配置信息
    def set_home_info(self, args):
        data =  json.loads(public.readFile(self.__config_path))
        data['ipv4'] = args.ipv4
        data['ipv6'] = args.ipv6
        data['dns_server'] = int(args.dns_server)
        # data['cdn_server'] = int(args.cdn_server)
        data['affect_num'] = int(args.affect_num)
        data['region_hw'] = args.region_hw
        data['region_ali'] = args.region_ali
        data['ttl'] = int(args.ttl)
        data['secretid'] = args.secretid.strip()
        data['secretkey'] = args.secretkey.strip()
        # data['key'] = args.key
        # data['data_server'] = int(args.data_server)
        public.writeFile(self.__config_path,json.dumps(data))
        return self.__response_json('',200,'数据保存成功')
    #从获取域名列表
    def get_domian_list(self, args):
        domains =  json.loads(public.readFile(self.__domians_path))
        data=[]
        for keys, values in domains.items():
            for key, value in values.items():
                data.append({'domain': keys, 'host': key , 'line': value})
        return self.__response_json(data)
    #设置域名信息
    def set_domian_info(self, args):
        if not args.host:
            return self.__response_json('',500,'主机名不能为空，请使用@创建空主机名。')
        domains =  json.loads(public.readFile(self.__domians_path))
        args.domain = args.domain.strip()
        args.host = args.host.strip()
        if args.domain not in domains:
            domains[args.domain] = {}
        domains[args.domain][args.host] = ["CM","CU","CT"]
        public.writeFile(self.__domians_path,json.dumps(domains))
        return self.__response_json('',200,'域名添加成功')
    #删除域名信息
    def del_domian_info(self, args):
        domains =  json.loads(public.readFile(self.__domians_path))
        if args.domain in domains: 
            if args.host in domains[args.domain]:
                del domains[args.domain][args.host]
            if not domains[args.domain]:
                del domains[args.domain]
        public.writeFile(self.__domians_path,json.dumps(domains))
        return self.__response_json('',200,'域名删除成功')
        
    #获取数据服务信息
    def get_data_server(self, args):
        data =  json.loads(public.readFile(self.__config_path))
        return self.__response_json(data,200,'获取数据成功')
        
    #设置数据服务信息
    def set_data_server(self, args):
        data =  json.loads(public.readFile(self.__config_path))
        data['key'] = args.key.strip()
        data['data_server'] = int(args.data_server)
        public.writeFile(self.__config_path,json.dumps(data))
        return self.__response_json('',200,'数据保存成功')

    #更新授权积分
    def update_integral(self, args):
        data =  json.loads(public.readFile(self.__config_path))
        provider_data =  json.loads(public.readFile(self.__provider_path))
        provider = [item for item in provider_data if item['id'] == data["data_server"]][0]
        headers = {'Content-Type': 'application/json'}
        response = requests.get(provider['get_license_url']+data["key"], headers=headers)
        if response.status_code == 200:
            res=response.json()
            data['integral'] = int(res['count'])
        # return self.__response_json(provider,200,'积分更新成功')
        public.writeFile(self.__config_path,json.dumps(data))
        return self.__response_json('',200,'积分更新成功')
        
    def __response_json(self, data, code=0, msg=''):
        response = {"code": code, "msg": msg, "data": data}
        return response

