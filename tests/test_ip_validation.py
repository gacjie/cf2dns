import gzip
import json
import socket
import ssl
import unittest
import zlib
from unittest.mock import MagicMock, patch

from cf2dns import redactions
from module.core import Engine
from module.log import RedactingLogger
from module.probe import MAX_BODY_BYTES, _DirectHTTPSConnection, _decode_body, probe_ip, record_hostname


# 依据错误预览和实际域名直连受限 IP 后请求 / 的真实 1034 响应。
# 两者实测都没有 cf-error-type；去掉域名、Ray ID、访问者 IP 等动态信息。
ERROR_JSON = json.dumps({
    'type': 'https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-1xxx-errors/error-1034/',
    'title': 'Error 1034: Edge IP Restricted', 'status': 403,
    'cloudflare_error': True, 'error_code': 1034, 'error_name': 'edge_ip_restricted',
}).encode()
ERROR_HTML = b'''<!doctype html><html><head>
<title>Edge IP Restricted | image.example.com | Cloudflare</title></head><body>
<div id="cf-error-details" class="p-0"><header>
<h1><span data-translate="error">Error</span>\n<span>1034</span></h1>
<h2>Edge IP Restricted</h2></header></div></body></html>'''


class ProbeTests(unittest.TestCase):
    def check_response(self, status, body, encoding='identity', error_type=''):
        with patch('module.probe._DirectHTTPSConnection') as factory:
            connection = factory.return_value
            response = connection.getresponse.return_value.__enter__.return_value
            response.status = status
            response.read.return_value = body
            headers = {'Content-Encoding': encoding, 'cf-error-type': error_type}
            response.getheader.side_effect = lambda name, default=None: headers.get(name, default)
            result = probe_ip('image.example.com', '192.0.2.1')
            connection.request.assert_called_once_with('GET', '/', headers={
                'Host': 'image.example.com', 'User-Agent': 'cf2dns/health-check',
                'Accept': 'application/problem+json',
                'Accept-Encoding': 'identity', 'Connection': 'close',
            })
            if error_type.strip() == '1034':
                response.read.assert_not_called()
            else:
                response.read.assert_called_once_with(MAX_BODY_BYTES)
            connection.getresponse.assert_called_once()
            connection.close.assert_called_once()
            return result

    def test_structured_1034_including_rewritten_http_status(self):
        for status in (200, 403, 530):
            with self.subTest(status=status):
                ok, reason = self.check_response(status, ERROR_JSON)
                self.assertFalse(ok)
                self.assertIn('1034', reason)

    def test_legacy_cloudflare_html(self):
        self.assertFalse(self.check_response(403, ERROR_HTML)[0])
        self.assertTrue(self.check_response(200, ERROR_HTML)[0])
        self.assertTrue(self.check_response(403, ERROR_HTML.replace(b'1034', b'1020'))[0])

    def test_diagnostic_header_without_reading_custom_page(self):
        self.assertFalse(self.check_response(403, b'custom page', error_type=' 1034 ')[0])
        self.assertTrue(self.check_response(403, b'custom page', error_type='1020')[0])
        self.assertTrue(self.check_response(403, b'custom page', error_type='10340')[0])

    def test_business_codes_and_mentions_are_not_cloudflare_errors(self):
        for body in (b'Edge IP Restricted', b'{"code": 1034}', b'error code: 1034',
                     b'{"error_code":1034}', b'{"cloudflare_error":false,"error_code":1034}',
                     b'{"cloudflare_error":"true","error_code":1034}',
                     b'<h1>Error 1034</h1><p>An article about Cloudflare</p>',
                     b'<script>' + ERROR_HTML + b'</script>'):
            with self.subTest(body=body):
                self.assertTrue(self.check_response(200, body)[0])
                self.assertTrue(self.check_response(403, body)[0])

    def test_http_policy_and_no_redirect_following(self):
        for status in (200, 204, 301, 302, 403, 404, 429, 500, 530):
            with self.subTest(status=status):
                self.assertTrue(self.check_response(status, b'ordinary page 1034')[0])
        other_error = ERROR_JSON.replace(b'1034', b'1020')
        self.assertTrue(self.check_response(403, other_error)[0])

    def test_compressed_errors_and_ordinary_responses(self):
        for encoding, compress in (('gzip', gzip.compress), ('deflate', zlib.compress)):
            with self.subTest(encoding=encoding):
                self.assertFalse(self.check_response(403, compress(ERROR_JSON), encoding)[0])
                self.assertFalse(self.check_response(403, compress(ERROR_HTML), encoding)[0])
                self.assertTrue(self.check_response(403, compress(b'Login required'), encoding)[0])
        raw_deflate = zlib.compress(ERROR_JSON)[2:-4]
        self.assertFalse(self.check_response(403, raw_deflate, 'deflate')[0])

    def test_decompression_is_bounded(self):
        compressed = gzip.compress(b'x' * (MAX_BODY_BYTES * 2))
        self.assertEqual(len(_decode_body(compressed, 'gzip')), MAX_BODY_BYTES)

    def test_truncated_compressed_response_is_inconclusive(self):
        for encoding, compress in (('gzip', gzip.compress), ('deflate', zlib.compress)):
            with self.subTest(encoding=encoding):
                ok, reason = self.check_response(403, compress(ERROR_JSON)[:12], encoding)
                self.assertFalse(ok)
                self.assertIn('检测未完成', reason)

    def test_unknown_or_invalid_encoding_is_inconclusive_not_1034(self):
        for encoding in ('gzip', 'br'):
            ok, reason = self.check_response(403, b'invalid compressed data', encoding)
            self.assertFalse(ok)
            self.assertIn('检测未完成', reason)
            self.assertNotIn('Cloudflare 1034', reason)

    def test_network_tls_and_read_failures_close_connection(self):
        for error in (socket.timeout('timed out'), ssl.SSLError('TLS failed')):
            with self.subTest(error=error), patch('module.probe._DirectHTTPSConnection') as factory:
                factory.return_value.getresponse.side_effect = error
                ok, reason = probe_ip('image.example.com', '192.0.2.1')
                self.assertFalse(ok)
                self.assertIn('检测未完成', reason)
                factory.return_value.close.assert_called_once()

    def test_direct_ipv4_ipv6_socket_uses_hostname_for_sni_and_certificate(self):
        for ip in ('192.0.2.1', '2001:db8::1'):
            with self.subTest(ip=ip), patch('module.probe.socket.create_connection') as connect:
                connection = _DirectHTTPSConnection('image.example.com', ip, 5)
                self.assertTrue(connection._context.check_hostname)
                self.assertEqual(connection._context.verify_mode, ssl.CERT_REQUIRED)
                context = MagicMock()
                connection._context = context
                connection.connect()
                connect.assert_called_once_with((ip, 443), 5)
                context.wrap_socket.assert_called_once_with(connect.return_value, server_hostname='image.example.com')
                connection.close()

    def test_tls_handshake_failure_closes_raw_socket(self):
        with patch('module.probe.socket.create_connection') as connect:
            connection = _DirectHTTPSConnection('image.example.com', '192.0.2.1', 5)
            connection._context = MagicMock()
            connection._context.wrap_socket.side_effect = ssl.SSLError('handshake')
            with self.assertRaises(ssl.SSLError):
                connection.connect()
            connect.return_value.close.assert_called_once()

    def test_hostname_from_config(self):
        self.assertEqual(record_hostname('Example.com.', '@'), 'example.com')
        self.assertEqual(record_hostname('example.com', 'image.cdn'), 'image.cdn.example.com')
        self.assertEqual(record_hostname('例子.com', '@'), 'xn--fsqu00a.com')
        for subdomain in ('*', '*.cdn', 'bad\r\nhost', 'https://image'):
            with self.subTest(subdomain=subdomain), self.assertRaises(ValueError):
                record_hostname('example.com', subdomain)

    def test_probe_hostname_is_redacted_after_case_and_idna_normalization(self):
        domains = {'Example.COM.': {'Image': ['CT']}, '例子.com': {'图像': ['CT']}}
        logger = RedactingLogger(MagicMock(), redactions({}, domains))
        for domain, subdomains in domains.items():
            for subdomain in subdomains:
                hostname = record_hostname(domain, subdomain)
                message = 'SKIP UNUSABLE IP: ----HOST: ' + hostname + '----MESSAGE: Cloudflare 1034'
                self.assertNotIn(hostname, logger.scrub(message))
                self.assertIn('Cloudflare 1034', logger.scrub(message))


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.logger = MagicMock()
        self.cloud = MagicMock()
        self.cloud.get_record.return_value = {
            'code': 0, 'data': {'domain': {'grade': 'Free'}, 'records': []},
        }
        for method in ('create_record', 'change_record', 'del_record'):
            getattr(self.cloud, method).return_value = {'code': 0}
        self.config = {'dns_server': 2, 'affect_num': 2}
        self.domains = {'example.com': {'image': ['CM', 'CU', 'CT', 'AB', 'DEF']}}
        self.candidates = {line: [{'ip': '192.0.2.1'}, {'ip': '192.0.2.2'}]
                           for line in ('CM', 'CU', 'CT')}

    def sync(self, result, iptype='v4'):
        engine = Engine(self.config, self.domains, [], self.logger)
        with patch.object(engine, '_get_optimization_ip', return_value={'code': 200, 'info': self.candidates}), \
                patch('module.core.probe_ip', side_effect=result) as probe:
            engine._sync(self.cloud, iptype)
        return probe

    def test_only_verified_ips_written_and_cache_shared_across_lines(self):
        probe = self.sync(lambda host, ip: (ip == '192.0.2.2', 'Cloudflare 1034'))
        self.assertEqual(probe.call_count, 2)
        self.assertEqual(self.cloud.create_record.call_count, 5)
        for call in self.cloud.create_record.call_args_list:
            self.assertEqual(call.args[2], '192.0.2.2')
        self.cloud.change_record.assert_not_called()

    def test_real_1034_response_rejected_but_business_403_can_be_written(self):
        self.domains = {'example.com': {'image': ['CM']}}
        self.candidates = {'CM': [{'ip': '162.159.138.65'}, {'ip': '192.0.2.2'}]}
        engine = Engine(self.config, self.domains, [], self.logger)

        def connection(hostname, ip, timeout):
            conn = MagicMock()
            response = conn.getresponse.return_value.__enter__.return_value
            response.status = 403
            response.read.return_value = ERROR_JSON if ip == '162.159.138.65' else b'{"code":1034,"message":"Login required"}'
            response.getheader.side_effect = lambda name, default=None: default
            return conn

        with patch.object(engine, '_get_optimization_ip', return_value={'code': 200, 'info': self.candidates}), \
                patch('module.probe._DirectHTTPSConnection', side_effect=connection):
            engine._sync(self.cloud, 'v4')
        self.cloud.create_record.assert_called_once_with('example.com', 'image', '192.0.2.2', 'A', '移动', 600)

    def test_domain_results_are_independent_and_apex_is_used(self):
        self.domains = {'example.com': {'@': ['CM'], 'image': ['CM']}}
        probe = self.sync(lambda host, ip: (host == 'example.com', 'result'))
        self.assertEqual(probe.call_count, 4)
        self.assertEqual(self.cloud.create_record.call_count, 2)
        self.assertTrue(all(call.args[1] == '@' for call in self.cloud.create_record.call_args_list))

    def test_all_rejected_or_empty_leaves_every_record_untouched(self):
        self.config['dns_server'] = 1
        for candidates in (self.candidates, {}):
            with self.subTest(candidates=candidates):
                self.candidates = candidates
                self.sync(lambda host, ip: (False, 'Cloudflare 1034'))
                self.assertEqual(self.cloud.mock_calls, [])

    def test_cname_cleanup_only_for_passing_lines(self):
        self.config['dns_server'] = 1
        self.domains = {'example.com': {'image': ['CM', 'CT']}}
        self.candidates = {'CM': [{'ip': '192.0.2.1'}], 'CT': [{'ip': '192.0.2.2'}]}
        def records(domain, limit, subdomain, kind):
            data = [{'id': 'bad', 'value': 'old.example.org', 'line': '移动'},
                    {'id': 'good', 'value': 'old.example.org', 'line': '电信'}] if kind == 'CNAME' else []
            return {'code': 0, 'data': {'domain': {'grade': 'Free'}, 'records': data}}
        self.cloud.get_record.side_effect = records
        self.sync(lambda host, ip: (ip == '192.0.2.2', 'result'))
        self.cloud.del_record.assert_called_once_with('example.com', 'good')
        self.cloud.create_record.assert_called_once()

    def test_query_failure_does_not_delete_cname(self):
        self.config['dns_server'] = 1
        self.cloud.get_record.return_value = {'code': -1, 'message': 'failed'}
        self.sync(lambda host, ip: (True, 'HTTP 200'))
        self.cloud.del_record.assert_not_called()
        self.cloud.create_record.assert_not_called()

    def test_keeps_verified_existing_ip_and_replaces_bad_one(self):
        self.domains = {'example.com': {'image': ['CM']}}
        self.cloud.get_record.return_value['data']['records'] = [
            {'id': 'bad', 'value': '192.0.2.3', 'line': '移动'},
            {'id': 'good', 'value': '192.0.2.1', 'line': '移动'},
        ]
        self.sync(lambda host, ip: (True, 'HTTP 200'))
        self.cloud.change_record.assert_called_once_with(
            'example.com', 'bad', 'image', '192.0.2.2', 'A', '移动', 600)
        self.cloud.create_record.assert_not_called()

    def test_replaces_bad_existing_before_filling_missing_record(self):
        self.domains = {'example.com': {'image': ['CM']}}
        self.cloud.get_record.return_value['data']['records'] = [
            {'id': 'bad', 'value': '192.0.2.3', 'line': '移动'},
        ]
        self.sync(lambda host, ip: (True, 'HTTP 200'))
        self.cloud.change_record.assert_called_once()
        self.cloud.create_record.assert_called_once()
        self.assertNotEqual(self.cloud.change_record.call_args.args[3], self.cloud.create_record.call_args.args[2])

    def test_rejected_candidates_never_fill_shortage(self):
        self.domains = {'example.com': {'image': ['CM']}}
        self.cloud.get_record.return_value['data']['records'] = [
            {'id': 'bad', 'value': '192.0.2.3', 'line': '移动'},
        ]
        self.sync(lambda host, ip: (ip == '192.0.2.2', 'result'))
        self.cloud.change_record.assert_called_once()
        self.cloud.create_record.assert_not_called()

    def test_new_record_shortage_is_logged(self):
        self.domains = {'example.com': {'image': ['CM']}}
        self.sync(lambda host, ip: (ip == '192.0.2.2', 'result'))
        self.cloud.create_record.assert_called_once()
        self.assertTrue(any('IP CANDIDATE SHORTAGE:' in call.args[0]
                            for call in self.logger.info.call_args_list))

    def test_ipv6_normalization_deduplication_and_wrong_family(self):
        self.domains = {'example.com': {'image': ['CT']}}
        self.candidates = {'CT': [{'ip': '2001:db8::1'}, {'ip': '2001:db8:0:0::1'},
                                  {'ip': '192.0.2.1'}, {'ip': 'not-an-ip'}]}
        probe = self.sync(lambda host, ip: (True, 'HTTP 200'), 'v6')
        probe.assert_called_once_with('image.example.com', '2001:db8::1')
        self.cloud.create_record.assert_called_once_with('example.com', 'image', '2001:db8::1', 'AAAA', '电信', 600)

    def test_wildcard_skipped_without_network_or_dns_changes(self):
        self.domains = {'example.com': {'*': ['CT']}}
        probe = self.sync(lambda host, ip: (True, 'HTTP 200'))
        probe.assert_not_called()
        self.assertEqual(self.cloud.mock_calls, [])


if __name__ == '__main__':
    unittest.main()
