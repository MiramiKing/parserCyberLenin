import asyncio
import collections
import io
import json
from datetime import datetime
from functools import partial

import bs4
from connection import Connectrequest
import pyppeteer
from grab import Grab
from pyppeteer_stealth import stealth

from natasha import (
    Segmenter,
    MorphVocab,

    NewsEmbedding,
    NewsMorphTagger,
    NewsSyntaxParser,
    NewsNERTagger,

    PER,
    LOC,
    NamesExtractor,
    DatesExtractor,
    MoneyExtractor,
    AddrExtractor,

    Doc
)
from wordcloud import WordCloud


class Parser():
    bs = partial(bs4.BeautifulSoup, features='lxml')
    connect = None
    connect2 = None
    page = None
    cat = None
    articles = []

    @classmethod
    async def setup(self):
        self.connect = await pyppeteer.launch(headless=True, args=['--no-sandbox'])

        self.page = await self.connect.newPage()
        await stealth(self.page)
        self.connect2 = Connectrequest()

    async def parseArticle(self, pages, sm):
        async with sm:
            try:
                for page in pages:
                    print(f"Парсинг страницы - {page}")
                    html = await self.connect2.get_html(page)
                    soup = self.bs(html)
                    authors = []
                    name = soup.find('i', {'itemprop': 'headline'}).text
                    authors_block = soup.find_all('meta', {'name': "citation_author"})
                    if authors_block:
                        authors = [author['content'].strip() for author in authors_block]
                    text_block = soup.find('div', {'class': 'ocr'})
                    text = text_block.text.strip()
                    labels = soup.find('div', {'class': 'labels'}).find_all('div', {'class': 'label'})
                    labels_text = [l.text for l in labels]
                    year = labels_text[0]
                    type = ','.join(labels_text[1:]) if len(labels) > 1 else ''
                    key_holder = soup.find('i', {'itemprop': 'keywords'})
                    key = key_holder.find_all('span') if key_holder else []
                    keys = [k.text.strip() for k in key]
                    description = soup.find('p', {'itemprop': 'description'})
                    annotation = description.text.strip() if description else ''
                    dat = {'name': name,
                           'year': year,
                           'type': type,
                           'authors': authors,
                           'keys': keys,
                           'annotation': annotation,
                           'text': text,
                           'url': page
                           }
                    self.articles.append(dat)
            except Exception as e:
                await asyncio.sleep(20)
                print(e)

    async def getCategoryCount(self, category: str):
        url = f'https://cyberleninka.ru/search?q={category}'
        self.cat = category
        await self.page.goto(url)
        html = await self.page.content()
        soup = self.bs(html)
        ul = soup.find('ul', {'class': 'paginator'})
        count = ul.find_all('li')[-1].find('a').text
        return count

    async def getCategoryCountPost(self, category, additional: dict = None):
        self.cat = category
        url = 'https://cyberleninka.ru/api/search'
        data = {"mode": "articles", "q": category, "size": 10, "from": 0}
        if additional:
            for k, v in additional.items():
                data[k] = v
        data = json.dumps(data,ensure_ascii=False)
        print(data)
        dat =await self.connect2.post(url=url, data=data)

        res = json.loads(dat)
        count = res['found']
        return count, res

    async def saveData(self, count: int):

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

        pages_part = await split_list(pages, 10)
        tasks = []
        sm = asyncio.Semaphore(25)
        print("Обработка статей")
        for part in pages_part:
            task = asyncio.ensure_future(self.parseArticle(part, sm))
            tasks.append(task)
        await asyncio.gather(*tasks)

        with io.open(r"result/data/ - " + self.cat + ".json", 'w', encoding='utf-8') as f:
            json.dump(self.articles, f, indent=4, ensure_ascii=False)
        print("Пасринг завершен")

    async def saveData_2(self, count: int, res):

        pages = []
        for art in res["articles"]:
            url = 'https://cyberleninka.ru' + art["link"]
            pages.append(url)

        pages_part = await split_list(pages, 1)
        tasks = []
        sm = asyncio.Semaphore(25)
        print("Обработка статей")
        for part in pages_part:
            task = asyncio.ensure_future(self.parseArticle(part, sm))
            tasks.append(task)
        await asyncio.gather(*tasks)

        with io.open(r"result/data/ - " + self.cat + ".json", 'w', encoding='utf-8') as f:
            json.dump(self.articles, f, indent=4, ensure_ascii=False)
        print("Пасринг завершен")

    async def close(self):
        await self.connect.close()
        await self.connect2.close()


async def split_list(alist, wanted_parts=1):
    length = len(alist)
    return [alist[i * length // wanted_parts: (i + 1) * length // wanted_parts]
            for i in range(wanted_parts)]


async def workWithArticles(data, work, sm):
    async with sm:
        for dat in data:
            t = await work.get_names(dat["text"])


async def start():
    work = Work()
    parser = Parser()
    await parser.setup()
    params = {}
    categrory = {
        1: {"name": 'ВАК', "id": 8},
        2: {"name": 'ARGIS', "id": 12},
        3: {"name": 'Scopus', "id": 2},
        4: {"name": 'RSCI', "id": 22},
        5: {"name": 'ESCI', "id": 21},
        6: {"name": 'WOS', "id": 1},
        7: {"name": 'zbMATH', "id": 24},
    }

    cat = input("Введите тему статей: ")
    years = input(
        "Введите период в годах рассматриваемых статей через пробел или оставьте пустым поле, чтобы поиск был за текущий год: ")
    if years:
        try:
            years_from, years_to = years.split(' ')
            params["year_from"] = int(years_from)
            params["year_to"] = int(years_to)
        except:
            params["year_from"] = int(years)

    print('Выберите начную базу или оставьте поле пустым: ')
    for k in categrory.keys():
        print(f'{k} - {categrory[k]["name"]}')
    base = input()
    if base:
        base_id = categrory[int(base)]["id"]
        params["catalogs"] = [base_id]
    articles = input("Введите количество рассматриваемых статей, по умолчанию 100: ")
    if not articles:
        articles = 100
    params["size"] = int(articles)
    count, res = await parser.getCategoryCountPost(category=cat,additional=params)
    print(f"Количество страниц в поисковике КиберЛеники - {count} ")
    await parser.saveData_2(int(count), res)
    await parser.close()

    data = parser.articles

    made_list = await split_list(data, 20)
    tasks = []
    sm = asyncio.Semaphore(10)
    print("Обработка статей")
    for part in made_list:
        task = asyncio.ensure_future(workWithArticles(part, work, sm))
        tasks.append(task)
    await asyncio.gather(*tasks)

    str_time = datetime.now().strftime('%m.%d.%y %H-%M-%S')
    await work.makeTagsCloud(str_time, work.tags)
    await work.savePersons(work.persons, str_time)
    print("Обработка завершена")


class Work():
    tags = []
    persons = []
    segmenter = Segmenter()
    morphVocab = MorphVocab()

    emb = NewsEmbedding()
    morphTagger = NewsMorphTagger(emb)
    syntaxTagger = NewsSyntaxParser(emb)
    nerTagger = NewsNERTagger(emb)

    names_extractor = NamesExtractor(morphVocab)
    dates_extractor = DatesExtractor(morphVocab)
    money_extractor = MoneyExtractor(morphVocab)
    addr_extractor = AddrExtractor(morphVocab)

    async def get_names(self, text):
        try:
            doc = Doc(text)
            doc.segment(self.segmenter)
            doc.tag_morph(self.morphTagger)
            doc.parse_syntax(self.syntaxTagger)
            doc.tag_ner(self.nerTagger)
            solves = []
            for token in doc.tokens:
                if (token.rel == "nsubj:pass" or token.rel == "amod" or token.rel == "nmod") and token.pos == "NOUN":
                    token.lemmatize(self.morphVocab)
                    solves.append(token.lemma)

            col = collections.Counter(solves).most_common()
            art_tags = [el[0] for el in col if el[1] > 5]
            for i in art_tags:
                self.tags.append(i)
            for span in doc.spans:
                if span.type == PER:
                    span.normalize(self.morphVocab)
                    span.extract_fact(self.names_extractor)

            diction = {_.normal: _.fact.as_dict for _ in doc.spans if _.fact}
            name_dict = set(diction)
            for i in name_dict:
                self.persons.append(i)
            # name_dict - Все имена, которые фигуррируют в тексте
        except Exception as e:
            print(e)

    async def makeTagsCloud(self, time, tags):
        try:
            tags_ = list(set(tags))
            wordcloud = WordCloud(width=2000,
                                  height=1500,
                                  random_state=1,
                                  background_color='black',
                                  margin=20,
                                  colormap='Pastel1',
                                  collocations=False, ).generate(" ".join(list(set(tags))))
            wordcloud.to_file(r"result/TagClouds/TagCloud - " + time + ".png")
        except Exception as e:
            print(e)

    async def savePersons(self, persons, str_time):
        print("Сохраняем результат...")
        persons_ = list(set(persons))
        try:
            with io.open(r"result/persons/person - " + str_time + ".json", 'w',
                         encoding='utf-8') as f:  # Выводим результат в Json файл
                json.dump(list(set(persons)), f, indent=4, ensure_ascii=False)
            return True
        except:
            return False


asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(start())
