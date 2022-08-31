# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

import requests
import json
from datetime import datetime


class AutoBookRecord:
    def __init__(self):
        self.input_title = None
        self.aladin = Aladin()
        self.book = None
        self.notion = Notion()
        self.get_target_book_title()

    def get_target_book_title(self):
        title = input('\nplease enter book title: ')
        self.input_title = title
        search_result = self.return_book_search(title)
        self.set_book_configuration(search_result[0])
        return title

    def return_book_search(self, title):
        json_info = self.request_book_info(title)
        return json_info

    def request_book_info(self, title):
        params = {'TTBKey': self.aladin.ttb_key, 'Query': title, 'Output': 'JS', 'Version': 20131101, 'Cover': 'Big'}
        response = requests.get(url=self.aladin.request_url, params=params)
        # print(json.loads(response.text)['item'])
        return self.trim_response_to_json(response)

    def trim_response_to_json(self, raw_response):
        return json.loads(raw_response.text)['item']

    def set_book_configuration(self, r):
        if self.input_title not in r['title']:
            print("no exact match")
            self.get_target_book_title()
            return

        # print(type(r))
        # print(len(r))
        # print(r)
        category_str = r['categoryName']
        categories = category_str.split('>')[-2:]
        # print(categories)
        self.book = Book(
            title=r['title'],
            author=r['author'],
            publisher=r['publisher'],
            image=r['cover'],
            info_url=r['link'],
            category=categories
        )
        # print(self.book.title, self.book.category, self.book.image, self.book.author, self.book.info_url)
        self.request_notion_database_post()

    def request_notion_database_post(self):
        if self.book is None:
            return

        request_header = {"Authorization": "Bearer " + self.notion.authorization_key, "Content-Type": "application/json", "Notion-Version": "2021-08-16"}
        request_body = self.trim_book_info_to_json()
        response = requests.post(url=self.notion.request_url, data=request_body, headers=request_header)
        # print(request_body)
        # print(response.text)
        # print(response.content)
        print("successfully done! check your notion :)")
        self.get_target_book_title()

    def trim_book_info_to_json(self):
        data = {}
        data["parent"] = self.build_parent_part_of_body()
        data["cover"] = self.build_cover_part_of_body()
        data["properties"] = self.build_properties_part_of_body()
        return json.dumps(data, ensure_ascii=False).encode('utf8')

    def build_parent_part_of_body(self):
        return {"database_id": self.notion.database_id}

    def build_cover_part_of_body(self):
        return {"type": "external", "external": {"url": self.book.image}}

    def build_properties_part_of_body(self):
        return {"title": {"title": [{"text": {"content": self.book.title}}]},
                "분류": {"multi_select": [{"name": self.book.category[-1]}, {"name": self.book.category[-2]}]},
                "지은이": {"rich_text": [{"type": "text", "text": {"content": self.book.author}}]},
                "출판사": {"rich_text": [{"type": "text", "text": {"content": self.book.publisher}}]},
                "책 정보(알라딘)": {"url": self.book.info_url},
                "읽은 날짜": {"date": {"start": datetime.now().isoformat()[:10], "end": None}}}


class Book:
    def __init__(self, title, author, publisher, image, info_url, category):
        self.title = title
        self.author = author
        self.publisher = publisher
        self.image = image
        self.info_url = info_url
        self.category = category


class Aladin:
    def __init__(self):
        self.request_url = "http://www.aladin.co.kr/ttb/api/ItemSearch.aspx"
        self.ttb_key = "ttbjeewoo05211857001"


class Notion:
    def __init__(self):
        self.request_url = "https://api.notion.com/v1/pages"
        self.authorization_key = "secret_EpOFfpWXo4HZBTGWOFqK3PV7nH69gkXNo9k5rC8f5bX"
        self.database_id = "8c46b8f8ad9d4dd3a299abdf84b5f98f"


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    My_Auto_Book_Record = AutoBookRecord()
