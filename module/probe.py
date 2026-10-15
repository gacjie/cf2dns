#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按真实访问域名探测候选 IP；不查询该域名的 DNS，也不经过环境代理。"""

import html
import http.client
import ipaddress
import json
import re
import socket
import ssl
import zlib

PROBE_TIMEOUT = 5
MAX_BODY_BYTES = 64 * 1024


def _is_1034(response, body):
    """只识别 Cloudflare 明确给出的 1034，不把业务错误码或普通 403 当作限制。

    官方格式：https://developers.cloudflare.com/fundamentals/reference/error-responses/
    cf-error-type 并非所有响应都有（错误预览接口实测缺失），必须兼容正文。
    """
    if response.getheader('cf-error-type', '').strip() == '1034':
        return True
    try:
        problem = json.loads(body)
    except ValueError:
        problem = None
    if isinstance(problem, dict):
        return problem.get('cloudflare_error') is True and problem.get('error_code') == 1034

    # 旧版/自定义 Error Page 可能忽略 Accept。仅在 403 响应中匹配标准错误页结构，
    # 避免含有“Error 1034”的文章、业务正文或脚本示例被误判。
    if response.status != 403:
        return False
    markup = re.sub(r'<!--.*?-->|<(script|style)\b[^>]*>.*?</\1\s*>', '', body,
                    flags=re.IGNORECASE | re.DOTALL)
    if not re.search(r'<div\b[^>]*\bid\s*=\s*[\"\']cf-error-details[\"\']', markup, re.IGNORECASE):
        return False

    def headings(tag):
        values = re.findall(r'<' + tag + r'\b[^>]*>(.*?)</' + tag + r'\s*>',
                            markup, re.IGNORECASE | re.DOTALL)
        return [re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]*>', ' ', value))).strip().lower()
                for value in values]

    return ('error 1034' in headings('h1') and 'edge ip restricted' in headings('h2')
            and any('cloudflare' in title for title in headings('title')))


def _decode_body(raw, encoding):
    """即使服务端忽略 identity，也可检查 gzip/deflate；解压同样有大小上限。"""
    if encoding in ('', 'identity'):
        decoded = raw
    elif encoding in ('gzip', 'deflate'):
        window = zlib.MAX_WBITS | 16 if encoding == 'gzip' else zlib.MAX_WBITS
        try:
            decoder = zlib.decompressobj(window)
            decoded = decoder.decompress(raw, MAX_BODY_BYTES)
        except zlib.error:
            if encoding != 'deflate':
                raise
            decoder = zlib.decompressobj(-zlib.MAX_WBITS)
            decoded = decoder.decompress(raw, MAX_BODY_BYTES)
        # decompress() 对截断数据可以不抛异常；不能把残缺正文当作“没有 1034”。
        # 达到读取/解压上限时则允许检查前缀，与未压缩响应的行为一致。
        if not decoder.eof and len(raw) < MAX_BODY_BYTES and len(decoded) < MAX_BODY_BYTES:
            raise ValueError('压缩响应不完整')
    else:
        raise ValueError('不支持的 Content-Encoding: ' + encoding)
    return decoded.decode('utf-8', errors='replace')


def record_hostname(domain, sub_domain):
    """@ 对应根域名；通配符不是实际访问域名，不能用它证明站点可用。"""
    hostname = domain if sub_domain in ('', '@') else sub_domain + '.' + domain
    hostname = hostname.rstrip('.').encode('idna').decode('ascii').lower()
    if len(hostname) > 253 or not all(
        re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', label)
        for label in hostname.split('.')
    ):
        raise ValueError('无法探测该主机名，请配置具体的完整域名（不支持通配符）')
    return hostname


class _DirectHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, hostname, ip, timeout):
        super().__init__(hostname, port=443, timeout=timeout,
                         context=ssl.create_default_context())
        self.ip = str(ipaddress.ip_address(ip))

    def connect(self):
        # TCP 目标是候选 IP，证书校验和 TLS SNI 则始终使用实际访问域名。
        raw = socket.create_connection((self.ip, self.port), self.timeout)
        try:
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except Exception:
            raw.close()
            raise


def probe_ip(hostname, ip, timeout=PROBE_TIMEOUT):
    """返回 (通过 1034 检查, 原因)。GET 保留错误正文，不跟随跳转。

    优先请求 Cloudflare 的结构化错误响应。普通 403/404/5xx 不代表 1034，
    不据此剔除候选；网络、TLS 或解码失败表示检测未完成，本轮暂不采用。
    """
    connection = None
    try:
        connection = _DirectHTTPSConnection(hostname, ip, timeout)
        connection.request('GET', '/', headers={
            'Host': hostname,
            'User-Agent': 'cf2dns/health-check',
            'Accept': 'application/problem+json',
            'Accept-Encoding': 'identity',
            'Connection': 'close',
        })
        with connection.getresponse() as response:
            # 明确的诊断头无需等待正文（自定义错误页也可能保留该头）。
            if response.getheader('cf-error-type', '').strip() == '1034':
                return False, 'Cloudflare 1034 (Edge IP Restricted), HTTP {}'.format(response.status)
            body = _decode_body(response.read(MAX_BODY_BYTES),
                                response.getheader('Content-Encoding', 'identity').strip().lower())
            if _is_1034(response, body):
                return False, 'Cloudflare 1034 (Edge IP Restricted), HTTP {}'.format(response.status)
            return True, 'HTTP {}，未检测到 Cloudflare 1034'.format(response.status)
    except (OSError, ValueError, http.client.HTTPException, zlib.error) as exc:
        return False, '检测未完成（非 1034 判定）: {}: {}'.format(type(exc).__name__, exc)
    finally:
        if connection is not None:
            connection.close()
