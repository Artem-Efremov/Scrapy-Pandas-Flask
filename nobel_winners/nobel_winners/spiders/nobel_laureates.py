# -*- coding: utf-8 -*-
import scrapy
import re
from urllib.parse import urljoin


class NobelLaureatesItem(scrapy.Item):
    
    name = scrapy.Field()
    link = scrapy.Field()
    year = scrapy.Field()
    category = scrapy.Field()
    country = scrapy.Field()
    gender = scrapy.Field()
    born_in = scrapy.Field()
    date_of_birth = scrapy.Field()
    date_of_death = scrapy.Field()
    place_of_birth = scrapy.Field()
    place_of_death = scrapy.Field()
    mini_bio = scrapy.Field()
    image_urls = scrapy.Field()
    bio_image = scrapy.Field()
    images = scrapy.Field()


class NobelLaureatesSpider(scrapy.Spider):
   
    name = 'nobel_laureates'
    allowed_domains = ['en.wikipedia.org']
    start_urls = ['https://en.wikipedia.org/wiki/List_of_Nobel_laureates_by_country']

    def parse(self, response):   
        # Method grabs all laureates by country
        for h3 in response.css('.mw-parser-output h3'):
            country = h3.css('.mw-headline::text').get()
            if country:
                laureates = h3.xpath('following-sibling::ol[1]')[0]
                for laureate in laureates.css('li'):
                    bio_link = urljoin(response.url, laureate.css('a::attr(href)').get())
                    request = scrapy.Request(url=bio_link, callback=self.parse_bio, dont_filter=True)
                    request.meta['item'] = NobelLaureatesItem(link=bio_link, **self.process_laureate_record(laureate, country))
                    yield request


    def process_laureate_record(self, laureate, country):
        link_text = laureate.xpath('descendant-or-self::text()')
        text = ''.join(link_text.getall())
        year = re.findall(r'\d{4}', text)
        category = re.findall(r'Chemistry|Economics|Literature|Peace|Physics|Physiology or Medicine', text)
        return {
            'name': link_text.get(),
            'year': (int(year[-1]) if year else 0),
            'category': (category[-1] if category else ''),
            'country': (country if '*' not in text else ''),
            'place_of_birth': (country if '*' in text else '')
        }


    def parse_bio(self, response):
        item = response.meta['item']

        img_src = response.css('table.infobox img::attr(src)')
        item['image_urls'] = [img_src.get()] if img_src else []

        mini_bio_lst = []
        for el in response.css('#mw-content-text > .mw-parser-output > *'):
            if el.attrib.get('id') == 'toc':
                break
            if el.xpath('self::p'):
                txt = ''.join(el.css('::text').getall()).strip()
                if txt:
                    mini_bio_lst.append(txt)
        mini_bio = '\n'.join(mini_bio)
        wikidata_link = response.css('#t-wikibase a::attr(href)').get()
        if wikidata_link:
            request = scrapy.Request(
                url=urljoin(re9sponse.url, wikidata_link),
                callback=self.parse_wikidata,
                dont_filter=True
            )
            request.meta['item'] = item
            yield request


    def parse_wikidata(self, response):
        item = response.meta['item']
        property_codes = [
            {'name': 'date_of_birth', 'code': 'P569'},
            {'name': 'date_of_death', 'code': 'P570'},
            {'name': 'place_of_birth', 'code': 'P19', 'add_tag': '/a'},
            {'name': 'place_of_death', 'code': 'P20', 'add_tag': '/a'},
            {'name': 'gender', 'code': 'P21', 'add_tag': '/a'}
        ]
        prop_xpath_pat = '//*[@id="{code}"]/div[2]/div/div/div[2]/div[1]/div/div[2]/div[2]/div[1]{add_tag}/text()'

        for prop in property_codes:
            sel = response.xpath(
                prop_xpath_pat.format(
                    code=prop['code'], 
                    add_tag=prop.get('add_tag', '')
                )
            )
            if sel:
                item[prop['name']] = sel.get()
        
        yield item