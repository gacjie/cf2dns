#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Mail: tongdongdong@outlook.com
#
# cf2dns 唯一入口。核心逻辑在 module/core.py，本文件只负责：取配置 → 建日志 → 调 run()。
#
# 两种运行形态，显式参数优先、否则按环境自动判定：
#
#   文件形态（宝塔插件 / 独立 python3 / Docker 挂载 config 目录）：配置只读 config/ 下的
#   JSON，日志写 cf2dns.log（本地私有文件，不脱敏；路径可用 CF2DNS_LOG_FILE 覆盖），
#   带启动随机延时
#       btpython /www/server/panel/plugin/cf2dns/cf2dns.py   # 宝塔计划任务，频率建议 ≥15 分钟
#       python3 cf2dns.py                                    # 独立部署 / 容器内由 entrypoint 反复调用
#
#   环境变量形态（GitHub Actions / Docker 的方式 B）：每项配置「环境变量优先，没设就回退 config/ 下的文件」，
#   日志打 stdout 且经过脱敏，不做启动延时（cron 本身就是错峰的，延时只会白占 runner 时间）
#       python cf2dns.py --env
#     CONFIG   → config/config.json          必需，两边都没有就 exit 1
#     DOMAINS  → config/domains.json         必需，两边都没有就 exit 1
#     PROVIDER → config/data_provider.json   用来传自定义优选源；没配就用随仓库分发的预置清单
#
# 注意：环境变量名仍是 PROVIDER，与文件名 data_provider.json 有意不一致 ——
# 现有用户的仓库 Secret 不会跟着改名，别顺手"修正"这处不对称。

import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from module.core import Engine
from module.log import Logger, PrintLogger, RedactingLogger, github_add_mask
from module.probe import record_hostname
from module.store import Store

#(环境变量名, 文件名, V1.15 之前的老文件名)
SOURCES = (
    ('CONFIG', 'config.json', None),
    ('DOMAINS', 'domains.json', None),
    ('PROVIDER', 'data_provider.json', 'provider.json'),
)

#config 里需要脱敏的字段：优选接口授权码与云厂商密钥
SECRET_FIELDS = ('key', 'secretid', 'secretkey')

#短于这个长度的串不脱敏：'@'（空主机名）与 CM/CT 这类线路码进了表，
#会把日志里无关的文字也替换成 ***。域名最短也有 4 个字符（a.io）
MIN_REDACT_LEN = 4


def use_env(argv):
    """判定运行形态：显式参数优先（两个都给时 --file 赢），否则看是不是 Actions 那种环境。

    GITHUB_ACTIONS 是 GitHub 必然注入的（=true），覆盖「用户手改过 run.yml、丢了 --env」
    的情况；CONFIG+DOMAINS 同时存在则覆盖在别处用环境变量配置的场景。单看 CONFIG 不够 ——
    这名字太通用，很可能是别人的变量，误判会让文件形态的用户拿一份不相干的配置去改解析记录。
    """
    if '--file' in argv:
        return False
    if '--env' in argv:
        return True
    if os.environ.get('GITHUB_ACTIONS'):
        return True
    return bool(os.environ.get('CONFIG')) and bool(os.environ.get('DOMAINS'))


def env_json(name, logger):
    """读一个 JSON 字符串环境变量。

    没设返回 None 交给调用方回退文件 —— 判空必须用 not raw：未设置的 Secret 在 workflow 里
    渲染成空字符串而不是"变量不存在"，写成 is None 会拿空串去 json.loads 报错。
    设了但不是合法 JSON 属于用户配错，直接非 0 退出，不静默回退到文件去改错的域名。
    """
    raw = os.environ.get(name)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except ValueError as e:   #JSONDecodeError 是 ValueError 的子类，其文本不含原文，可安全打印
        logger.error('环境变量 ' + name + ' 不是合法 JSON：' + str(e))
        sys.exit(1)


def load_inputs(env_mode, store, logger):
    """按形态取三份配置，返回 [config, domains, provider_data]，取不到的项为 None。

    文件形态不看环境变量：宝塔机器上万一有个同名的 CONFIG 变量，不该影响解析。
    """
    values = []
    for env_name, file_name, legacy_name in SOURCES:
        value = env_json(env_name, logger) if env_mode else None
        if value is None:
            #路径解析统一走 Store.path()，否则会出现界面写 config/config.json、
            #执行脚本仍读根目录 config.json 的分裂情况
            value = store.read_json(store.path(file_name, legacy_name))
        values.append(value)
    return values


def redactions(config, domains):
    """收集需要从 Actions 日志里抹掉的串：密钥、授权码、域名、子域名、完整域名。

    完整域名也要收：厂商报错里常常带的是 www.example.com 这种整串。
    新增敏感字段要同步改 SECRET_FIELDS，否则会直接打到公网日志里。
    """
    values = set()
    for field in SECRET_FIELDS:
        values.add(str((config or {}).get(field) or ''))
    for domain, sub_domains in (domains or {}).items():
        values.add(str(domain))
        # 探测会将域名小写化并转成 IDNA；公开日志也必须屏蔽这些规范形式。
        try:
            values.add(record_hostname(domain, '@'))
        except (TypeError, ValueError):
            pass
        for sub_domain in (sub_domains or {}):
            values.add(str(sub_domain))
            if sub_domain and sub_domain != '@':
                values.add('{}.{}'.format(sub_domain, domain))
            try:
                values.add(record_hostname(domain, sub_domain))
            except (TypeError, ValueError):
                pass
    return {v for v in values if len(v) >= MIN_REDACT_LEN}


def log_file():
    """文件形态的日志落点，默认脚本目录下的 cf2dns.log。

    CF2DNS_LOG_FILE 是给 Docker 用的：容器里 /app/cf2dns.log 随容器重建就丢了，
    想持久化只能落到挂载出来的 config/ 目录下。

    这是「文件形态不看环境变量」的一处例外，与那条原则不冲突 —— 那条针对的是三份
    配置数据（config/domains/provider），误读别人的同名变量会去改不相干的解析记录；
    日志路径没有这个风险。变量名带 CF2DNS_ 前缀，避免撞上通用名字。
    """
    return os.environ.get('CF2DNS_LOG_FILE') or os.path.join(BASE_DIR, 'cf2dns.log')


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    env_mode = use_env(argv)
    logger = PrintLogger() if env_mode else Logger(log_file(), level='debug').logger

    #载入阶段的报错只含变量名/文件名，不含配置内容，所以可以先用未脱敏的 logger
    config, domains, provider_data = load_inputs(env_mode, Store(BASE_DIR), logger)

    if env_mode:
        #必须赶在引擎跑起来之前注册屏蔽，否则第一条日志就漏了
        secrets = redactions(config, domains)
        github_add_mask(secrets)
        logger = RedactingLogger(logger, secrets)

    def abort(message):
        """必需配置缺失：环境变量形态退非 0，否则 workflow 显示成功、用户不会发现解析早停了。

        文件形态维持原行为（记日志、退 0）。
        """
        #不能写成"环境变量未设置"：变量设了但内容是空对象时也会走到这里
        logger.error(message + ('（环境变量与 config/ 下的文件都没取到可用内容）' if env_mode else ''))
        if env_mode:
            sys.exit(1)

    if not config:
        return abort('读取配置失败：config.json 缺失或内容不是合法 JSON')
    if not domains:
        #core._sync 遇到空 domains 直接 return 且一条日志都不记，不在这里拦住就是一次静默空跑
        return abort('没有可解析的域名：domains.json 缺失或为空')
    if not provider_data:
        return abort('读取优选接口配置失败：data_provider.json 缺失或内容不是合法 JSON')

    Engine(config, domains, provider_data, logger).run(startup_delay=not env_mode)


if __name__ == '__main__':
    main()
