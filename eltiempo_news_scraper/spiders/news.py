import re
import csv
import random
from datetime import date, timedelta
import scrapy

import csv

from sqlalchemy import except_

file = open("eltiempo_news_scraper/utils/user_agent_list.csv")
AGENTS = csv.reader(file)
header = next(AGENTS)
AGENTS = list(map(lambda agent: agent[0], AGENTS))
file.close()

class NewsSpider(scrapy.Spider):
    name = 'news'
    allowed_domains = ['www.eltiempo.com']

    def start_requests(self):
        
        # search_terms = [term.upper() for term in self.search_terms.split(',')]

        # start_year, start_month = [int(date_element) for date_element in self.start_date.split('-')]
        # end_year, end_month = [int(date_element) for date_element in self.end_date.split('-')]

        search_terms = ['']

        start_year, start_month, start_day = 2010, 1, 1
        end_year, end_month, end_day = 2022, 5, 31
        end_date = date(end_year, end_month, end_day)

        for term in search_terms:
            
            temp_date = date(start_year, start_month, start_day)
            
            while temp_date <= end_date:
                temp_date_str = temp_date.strftime('%Y-%m-%d')
                target_url = f'https://www.eltiempo.com/buscar?q={term}&publishedAt%5Bfrom%5D={temp_date_str}&publishedAt%5Buntil%5D={temp_date_str}&contentTypes%5B0%5D=article'

                yield scrapy.Request(url = target_url, callback = self.parse, headers = {'User-Agent': random.choice(AGENTS)}, meta = {'search_term': term})
                
                temp_date = temp_date + timedelta(days = 1)

    def parse(self, response):
        news_items = response.xpath('//div[contains(@class,"default-listing")]/div[contains(@class, "listing")]')
        
        for item in news_items:
            item_category = item.xpath('.//div[@class="category"]/text()').get().lower()
            item_absolute_url = response.urljoin(item.xpath('.//h3[@class="title-container"]/a/@href').get())
            item_timestamp = item.xpath('.//div[@class="published-at"]/@published-unix').get()
            
            meta_info = response.request.meta.copy()

            if item_category not in ('contenido patrocinado', 'historias el tiempo'):
                
                meta_info.update({'news_category': item_category, 'news_url_absolute': item_absolute_url, 'item_timestamp': item_timestamp})

                yield scrapy.Request(url = item_absolute_url, callback = self.parse_item, headers = {'User-Agent': random.choice(AGENTS)}, meta = meta_info)

        next_page = response.xpath('//li[@class="next"]/a/@href').get()

        if next_page:
            yield scrapy.Request(url = response.urljoin(next_page), callback = self.parse, headers = {'User-Agent': random.choice(AGENTS)}, meta = response.request.meta)

    def parse_item(self, response):

        item_title = response.xpath('normalize-space(//div[@class="titular"]//h1/text())').get()
        item_subtitle = response.xpath('normalize-space(//div[contains(@class, "lead")]/p/text())').get()

        stop_element = response.xpath('((//span[contains(@class,"articulo-subtitulo")])[contains(text(), "noticias") and position() = last()])')

        if stop_element:
            paragraphs = stop_element.xpath('./preceding::p[contains(@class, "contenido")]')
        else:
            paragraphs = response.xpath('//p[contains(@class, "contenido")]')

        def _join_text_recursively(selector):
            output_str = ''

            if not (selector.xpath('./child::node()') or re.search('^<.*>$', selector.get())):
                return selector.get()
            
            return output_str + ''.join([_join_text_recursively(selector) for selector in selector.xpath('./child::node()')])

        def _remove_anchors(paragraph_selector, joined_text):

            MAX_OFFSET = 32

            try:
                for anchor_str_content in paragraph_selector.xpath('.//a/text()').getall():
                    left_idx = joined_text.index(anchor_str_content)

                    anchor_lenght = len(anchor_str_content)
                    middle_idx = left_idx + anchor_lenght // 2

                    phase = left_phase = right_phase = 0
                    is_left_found = is_right_found = False

                    while not (is_left_found and is_right_found):
                        if phase - anchor_lenght // 2 > MAX_OFFSET:
                            break
                        if not is_left_found and middle_idx - phase >= 0 and joined_text[middle_idx - phase] == '(':
                            is_left_found = True
                            left_phase = phase
                        if not is_right_found and middle_idx + phase < len(joined_text) and joined_text[middle_idx + phase] == ')':
                            is_right_found = True
                            right_phase = phase
                        phase += 1

                    if is_left_found and is_right_found:
                        joined_text = joined_text[:middle_idx - left_phase] + joined_text[middle_idx + right_phase + 1:]
            except:
                pass
            finally:
                return joined_text

        full_news_text = ''

        for paragraph in paragraphs:
            full_news_text += _remove_anchors(paragraph, _join_text_recursively(paragraph))

        yield {
            'search_term': response.request.meta['search_term'],
            'news_category': response.request.meta['news_category'],
            'news_url_absolute': response.request.meta['news_url_absolute'],
            'news_exact_date': date.fromtimestamp(int(response.request.meta['item_timestamp'])).strftime('%Y-%m-%d'),
            'news_title': item_title,
            'news_subtitle': item_subtitle,
            'news_text_content': full_news_text.replace('\n', '') if full_news_text else ''
        }
        
                    



        
        


        



        

