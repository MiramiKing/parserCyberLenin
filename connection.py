import csv
import os
import json
import ssl
import random
import requests
import aiohttp
from proxy import select_proxies

class Connection():
    def __init__(self):
        self.head = [
            'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:80.0) Gecko/20100101 Firefox/80.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.83 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36 OPR/71.0.3770.171']
        self.session = requests.Session()

    def get_html(self, link, cookies=None, header: dict = None, data=None, post=False):
        if header:
            self.session.headers.update(header)
        self.session.headers.update({'User-Agent': random.choice(self.head)})
        if cookies:
            return self.session.get(link, cookies=cookies, timeout=30, data=data).text
        if post:
            return self.session.post(link, timeout=30, data=data).text
        else:
            return self.session.get(link, timeout=30).text

    def close(self):
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()

    def write_csv(self, data, file_name, arg='a'):
        with open('{}.csv'.format(file_name), arg, encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow((data['name'], data['url']))

    def write_json(self, data, filename='- интероперабельность.json'):
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)

class Connectrequest(object):
    def __init__(self):
        self.session = None
        FORCED_CIPHERS = (
            'ECDH+AESGCM:DH+AESGCM:ECDH+AES256:DH+AES256:ECDH+AES128:DH+AES:ECDH+HIGH:'
            'DH+HIGH:ECDH+3DES:DH+3DES:RSA+AESGCM:RSA+AES:RSA+HIGH:RSA+3DES'
        )
        self.sslcontext = ssl.create_default_context()
        # self.sslcontext.options |= ssl.OP_NO_SSLv3
        # self.sslcontext.options |= ssl.OP_NO_SSLv2
        # self.sslcontext.options |= ssl.OP_NO_TLSv1_1
        # self.sslcontext.options |= ssl.OP_NO_TLSv1_2
        self.sslcontext.options |= ssl.OP_NO_TLSv1_3
        self.sslcontext.set_ciphers(FORCED_CIPHERS)

        self.head = [
            'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:80.0) Gecko/20100101 Firefox/80.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.83 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36 OPR/71.0.3770.171']

    async def get_html(self, url, cookies=None, header: dict = None, site=None):
        try:
            if self.session is None:
                self.session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=50, verify_ssl=False),
                                                     cookies=cookies)

            self.headers = {'User-Agent': str(random.choice(self.head))}
            if header:
                self.headers.update(header)

            proxies = select_proxies(site)
            if proxies:
                proxy_ = random.choice(proxies)
                proxy = 'http://{}'.format(proxy_)
            async with self.session.get(url, headers=self.headers, proxy=proxy, timeout=100,
                                        ssl=self.sslcontext) as response:
                results = response.text()
                return await results
        except Exception as e:
            print(url)
            #traceback.print_exc()
            print(e)
            # await self.close()

    async def close(self):
        await self.session.close()