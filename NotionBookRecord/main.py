import requests
import json
from datetime import datetime


class AutoBookRecord:
    def __init__(self):
        self.aladin = Aladin()
        self.notion = Notion()
        self.book = None
        self.execute_auto_book_record()

    def execute_auto_book_record(self):
        title = self.get_target_book_title()

        if self.is_not_valid(title):
            self.reset()
            return
        candidate_book_list = self.get_book_info_list(title)
        chosen_book_index_num = self.request_user_book_choice(candidate_book_list)
        book = candidate_book_list[chosen_book_index_num]
        self.set_book_configuration(book)

        result = self.post_book_info_to_notion()
        self.notify_result_to_user(result)

    def reset(self):
        self.book = None
        self.execute_auto_book_record()

    def get_target_book_title(self):
        title = input('\nplease enter book title: ')
        return title

    def get_book_info_list(self, title):
        response = self.request_book_info(title)
        result = self.trim_response_to_json(response)
        if len(result) < 1:
            print('There\'s no matching result.')
            self.reset()
            return
        # if result has no element, it means there's no matching result
        return result

    def request_user_book_choice(self, candidate_book_list):
        candidate_book_list_for_print = []
        for i, book in enumerate(candidate_book_list):
            title = book['title']
            author = book['author']
            publisher = book['publisher']
            pub_date = book['pubDate']

            candidate_book_list_for_print.append(f'{i + 1}) title: {title}\n   author: {author}\n   publisher: {publisher}\n   pubDate: {pub_date}')

        # ------------------------ printed for user ------------------------
        print('\nBelow books were found according to your input\n')
        for book in candidate_book_list_for_print:
            print(book)
        chosen_book_index_str = input('\nPlease enter the number of the book you want to add: ')
        # ------------------------ printed for user ------------------------

        chosen_book_index_num = 0
        while chosen_book_index_num < 1:
            # check only integer was entered
            try:
                chosen_book_index_num = int(chosen_book_index_str)
            except ValueError:
                chosen_book_index_str = input(f'Enter proper number(1 ~ {len(candidate_book_list)}) only: ')

            # check proper range of integer was entered
            if not 0 < chosen_book_index_num < 11:
                chosen_book_index_num = 0
                chosen_book_index_str = input(f'Enter proper number(1 ~ {len(candidate_book_list)}) only: ')
                continue

        return chosen_book_index_num - 1

    def request_book_info(self, title):
        params = {'TTBKey': self.aladin.ttb_key, 'Query': title, 'Output': 'JS', 'Version': 20131101, 'Cover': 'Big'}
        response = requests.get(url=self.aladin.request_url, params=params)
        return response

    def trim_response_to_json(self, raw_response):
        return json.loads(raw_response.text)['item']

    def set_book_configuration(self, book):
        b = book
        categories = self.parse_category(b['categoryName'])
        authors = self.parse_author(b['author'])

        self.book = Book(
            title=b['title'],
            author=authors,
            publisher=b['publisher'],
            image=b['cover'],
            info_url=b['link'],
            category=categories
        )

    def parse_category(self, category_str):
        categories = category_str.split('>')
        if len(categories) >= 2:
            categories = categories[1:]
        return categories

    def parse_author(self, author_str):
        author_list = []
        authors = author_str.split(', ')
        for author in authors:
            if '옮긴이' not in author:
                author_list.append(author.replace(' (지은이)', ''))
        return ', '.join(author_list)

    def post_book_info_to_notion(self):
        result = self.request_notion_database_post()
        return result

    def request_notion_database_post(self):
        if self.book is None:
            return

        request_header = {"Authorization": "Bearer " + self.notion.authorization_key, "Content-Type": "application/json", "Notion-Version": "2021-08-16"}
        request_body = self.trim_book_info_to_json()
        response = requests.post(url=self.notion.request_url, data=request_body, headers=request_header)
        if '200' in str(response):
            return True
        return False

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
                "분류": {"multi_select": [{"name": c} for c in self.book.category]},
                "지은이": {"rich_text": [{"type": "text", "text": {"content": self.book.author}}]},
                "출판사": {"rich_text": [{"type": "text", "text": {"content": self.book.publisher}}]},
                "책 정보(알라딘)": {"url": self.book.info_url},
                "읽은 날짜": {"date": {"start": datetime.now().isoformat()[:10], "end": None}}}

    def is_not_valid(self, input):
        if input is None or type(input) != str or input == "":
            return True
        return False

    def notify_result_to_user(self, result):
        if result:
            print("Successfully done! It might take few seconds.\nPlease check your notion :)")
        else:
            print("Something got wrong. Please try again.")
        self.reset()


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
