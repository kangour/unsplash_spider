import os
import sys
import json
import urllib
import requests
import collections
from bs4 import BeautifulSoup
from multiprocessing import Pool
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


'''
爬取：unsplash 免版权图片分享网站首页

作者：不才
邮箱：laobingm@qq.com
结构：Base 请求基类，Soup 数据爬取，Parser 通用元素解析，Pager 页面数据解析，Operater 操作部分，Store 文件存储
待做：多线程同步爬取和下载，Session 缓存，Except 异常处理
日期：2019年5月21日
更新：
协作：

'''

class Base():
    def __init__(self):
        self._http = requests.Session()

    def handle_result(self, res):
        return res

    def request(self, method, url, **kwargs):
        res = self._http.request(
            method=method,
            url=url,
            **kwargs
        )
        return self.handle_result(res)

    def get(self, url, **kwargs):
        return self.request(
            method='get',
            url=url,
            **kwargs
        )

    def post(self, url, **kwargs):
        return self.request(
            method='post',
            url_or_endpoint=url,
            **kwargs
        )


class Soup(Base):
    def __init__(self, target, data_type):
        super().__init__()
        self.target = target
        self.data_type = data_type
        self.soup = self.get_soup()

    def get_soup(self):
        res = self.get(url=self.target)
        if self.data_type == 'html':
            return BeautifulSoup(res, 'lxml')
        elif self.data_type == 'json':
            return json.loads(res.text)
        else:
            raise TypeError('document type error')


class Parser():
    def __init__(self, target, data_type):
        self.soup = Soup(target, data_type).soup

    def get_element(self, tag, attrs={}, find_all=False):
        if find_all is False:
            return self.soup.find(name=tag, attrs=attrs)
        else:
            return self.soup.find_all(name=tag, attrs=attrs)

    @staticmethod
    def get_element_by_subsoup(soup, tag, attrs={}, find_all=False):
        if find_all is False:
            return soup.find(name=tag, attrs=attrs)
        else:
            return soup.find_all(name=tag, attrs=attrs)

    @staticmethod
    def format_url(target):
        if target.startswith('//'):
            target = 'https:' + target
        return target


class Store():
    def __init__(self, filename='result', suffix='.txt', path='./'):
        self.filename = filename
        self.suffix = suffix
        self.path = path
        self.check_filename()

    def check_filename(self):
        '''
        清理同名文件
        '''
        for f in os.listdir(self.path):
            fullname = os.path.join(self.path, f)
            if os.path.isfile(fullname) and f == self.filename + self.suffix:
                logger.warn('{} already exists, remove it!'.format(self.filename + self.suffix))
                os.remove(os.path.join(self.path, f))

    def writer(self, *content):
        with open(self.path + self.filename + self.suffix, 'a') as f:
            for i in content:
                f.write(i)
                f.write('\n\n')

    def reporthook(self, got_block, block_size, file_size):
        progress = min(int(got_block * block_size / file_size * 100), 100)
        sys.stdout.write('\r|{}{}| {}% {:.2f}M / {:.2f}M'.format(progress * '▇', (100 - progress) * ' ', progress, got_block * block_size / 1024 / 1024, file_size / 1024 / 1024))

    def download(self, url):
        fullname = self.path + self.filename + self.suffix
        urllib.request.urlretrieve(url, fullname, self.reporthook)
        sys.stdout.write('\n')
        logger.info('{} download complete!'.format(self.filename + self.suffix))


class Pager(Parser):
    def __init__(self, target, data_type):
        target = self.format_url(target)
        super().__init__(target, data_type)

    def images(self):
        soup = self.soup
        dic = collections.OrderedDict()
        for i in soup:
            dic[i['id']] = i['urls']['raw']
            logger.info('{0}'.format(i['urls']['raw']))
        return dic


class Operater():
    def __init__(self, target, data_type='html'):
        print(target)
        self.page = Pager(target, data_type)

    def get_images(self):
        res = self.page.images()
        return res


def spider(image):
    name = image[0]
    url = image[1]
    logger.info('{} 开始下载'.format(name))
    store = Store(filename=name, suffix='.jpg', path='./')
    store.download(url)


if __name__ == '__main__':
    homepage = 'https://unsplash.com/napi/photos?page={}&per_page=30'
    # 页面级，爬 100 页
    for i in range(100):
        operater = Operater(homepage.format(i + 1), data_type='json')
        images = operater.get_images()
        logger.info('列表获取完成！')
        # 多进程，每个进程对应一张图
        p = Pool(len(images))
        for i in range(len(images)):
            p.apply_async(spider, args=(images.popitem(),))
        p.close()
        p.join()
