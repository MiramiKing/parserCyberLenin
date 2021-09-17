import asyncio
import io
import json
from functools import partial

import bs4
from connection import Connectrequest
import pyppeteer
from grab import Grab
from pyppeteer_stealth import stealth


class Parser():
    bs = partial(bs4.BeautifulSoup, features='lxml')
    connect = None
    connect2 = None
    page = None
    data = []
    cat = None

    @classmethod
    async def setup(self):
        self.connect = await pyppeteer.launch(headless=True, args=['--no-sandbox'])

        self.page = await self.connect.newPage()
        await stealth(self.page)
        self.connect2 = Connectrequest()

    async def getCategoryCount(self, category: str):
        url = f'https://cyberleninka.ru/search?q={category}'
        self.cat = category
        await self.page.goto(url)
        html = await self.page.content()
        soup = self.bs(html)
        ul = soup.find('ul', {'class': 'paginator'})
        count = ul.find_all('li')[-1].find('a').text
        return count

    async def saveData(self, count: int):
        articles = []
        pages = []
        for i in range(1, count + 1):
            url = f'https://cyberleninka.ru/search?q={self.cat}&page={i}'
            await self.page.goto(url)
            await asyncio.sleep(5)
            html = await self.page.content()
            soup = self.bs(html)
            ul = soup.find('ul', {'id': 'search-results'})
            lis = ul.find_all('li')
            for li in lis:
                pages.append('https://cyberleninka.ru' + li.find('a')['href'])

        for page in pages:
            html = await self.connect2.get_html(page)
            soup = self.bs(html)
            name = soup.find('i', {'itemprop': 'headline'}).text
            labels = soup.find('div', {'class': 'labels'}).text.replace('\n', '', 1).split('\n')
            year = labels[0]
            type = labels[1]
            key_holder = soup.find('i', {'itemprop': 'keywords'})
            key = key_holder.find_all('span') if key_holder else []
            keys = [k.text.strip() for k in key]
            description = soup.find('p', {'itemprop': 'description'})
            annotation = description.text.strip() if description else ''
            dat = {'name': name,
                   'year': year,
                   'type': type,
                   'keys': keys,
                   'annotation': annotation,
                   'url': page
                   }
            articles.append(dat)
            print(dat)
        print(pages)
        with io.open('data.json','w',encoding='utf-8') as f:
            json.dump(articles, f, indent=4,ensure_ascii=False)

    async def close(self):
        await self.connect.close()
        await self.connect2.close()


async def start():
    parser = Parser()
    await parser.setup()
    count = await parser.getCategoryCount(category='java')
    print(count)
    await parser.saveData(int(count))

    await parser.close()


asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(start())
