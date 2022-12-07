import sys
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
        title = input_w_timeout('\nplease enter book title: ')
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

            candidate_book_list_for_print.append(
                f'{i + 1}) title: {title}\n   author: {author}\n   publisher: {publisher}\n   pubDate: {pub_date}')

        # ------------------------ printed for user ------------------------
        print('\nBelow books were found according to your input\n')
        for book in candidate_book_list_for_print:
            print(book)
        print('\nYou can press \'b\' to go back.')
        chosen_book_index_str = input_w_timeout('Please enter the number of the book you want to add: ')
        # ------------------------ printed for user ------------------------

        chosen_book_index_num = 0
        while chosen_book_index_num < 1:
            if chosen_book_index_str == 'b':
                self.reset()
                return

            if chosen_book_index_str in list(map(str, range(1, len(candidate_book_list) + 1))):
                chosen_book_index_num = int(chosen_book_index_str)
            else:
                chosen_book_index_str = input_w_timeout(f'Enter proper number(1 ~ {len(candidate_book_list)}) only: ')

        return chosen_book_index_num - 1

    def request_book_info(self, title):
        params = {'TTBKey': self.aladin.ttb_key, 'Query': title, 'Output': 'JS', 'Version': 20131101, 'Cover': 'Big'}
        response = requests.get(url=self.aladin.request_url, params=params)
        return response

    def trim_response_to_json(self, raw_response):
        return json.loads(raw_response.text)['item']

    def set_book_configuration(self, book):
        b = book
        p = self.parse_author_w_translator(b['author'])
        author = p['author']
        translator = p['translator']

        self.book = PictureBook(
            title=b['title'],
            pub_date=b['pubDate'][:3],
            author=author,
            publisher=b['publisher'],
            translator=translator,
            image=b['cover'],
            info_url=b['link']
        )

    def parse_category(self, category_str):
        categories = category_str.split('>')
        if len(categories) < 2:
            return ''
        return categories[1]

    def parse_author_w_translator(self, author_str):
        author_list = []
        default_translator = '-'
        authors = author_str.split(', ')
        for author in authors:
            if '옮긴이' not in author:
                author_list.append(author.replace(' (지은이)', ''))
            else:
                default_translator = author.replace('(옮긴이)', '')

        return {'author': ', '.join(author_list), 'translator': default_translator}

    def post_book_info_to_notion(self):
        result = self.request_notion_database_post()
        return result

    def request_notion_database_post(self):
        if self.book is None:
            return

        request_header = {"Authorization": "Bearer " + self.notion.authorization_key,
                          "Content-Type": "application/json", "Notion-Version": "2021-08-16"}
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
        properties = {"title": {"title": [{"text": {"content": self.book.title}}]},
                "지은이": {"rich_text": [{"type": "text", "text": {"content": self.book.author}}]},
                "출판사": {"select": {"name": self.book.publisher}},
                "번역": {"rich_text": [{"type": "text", "text": {"content": self.book.translator}}]},
                "책 정보(알라딘)": {"url": self.book.info_url},
                "진행도": {"select": {"name": "N"}}}

        return properties

    def is_not_valid(self, input):
        if input is None or type(input) != str or input == "":
            return True
        return False

    def notify_result_to_user(self, result):
        if result:
            print("\nSuccessfully done! It might take few seconds.\nPlease check your notion :)")
        else:
            print("\nSomething got wrong. Please try again.")
        self.reset()


class PictureBook:
    def __init__(self, title, pub_date, author, publisher, translator, image, info_url):
        self.title = title
        self.pub_date = pub_date
        self.author = author
        self.publisher = publisher
        self.translator = translator
        self.image = image
        self.info_url = info_url


class Aladin:
    def __init__(self):
        self.request_url = "http://www.aladin.co.kr/ttb/api/ItemSearch.aspx"
        self.ttb_key = "ttbjeewoo05211857001"


class Notion:
    def __init__(self):
        self.request_url = "https://api.notion.com/v1/pages"
        self.authorization_key = "secret_EpOFfpWXo4HZBTGWOFqK3PV7nH69gkXNo9k5rC8f5bX"
        self.database_id = "0abdfdf5a58341488815963dae0fa8f4"
        # 그림숲산책 데이터베이스 url last string


# https://greenfishblog.tistory.com/257
def input_timer(prompt, timeout_sec):
    import subprocess
    import sys
    import threading

    class Local:
        # check if timeout occurred
        _timeout_occurred = False

        def on_timeout(self, process):
            self._timeout_occurred = True
            process.kill()
            # clear stdin buffer (for linux)
            # when some keys hit and timeout occurred before enter key press,
            # that input text passed to next input().
            # remove stdin buffer.
            try:
                import termios
                termios.tcflush(sys.stdin, termios.TCIFLUSH)
            except ImportError:
                # windows, just exit
                pass

        def input_timer_main(self, prompt_in, timeout_sec_in):
            # print with no new line
            print(prompt_in, end="")

            # print prompt_in immediately
            sys.stdout.flush()

            # new python input process create.
            # and print it for pass stdout
            cmd = [sys.executable, '-c', 'print(input())']
            with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as proc:
                timer_proc = threading.Timer(timeout_sec_in, self.on_timeout, [proc])
                try:
                    # timer set
                    timer_proc.start()
                    stdout, stderr = proc.communicate()

                    # get stdout and trim new line character
                    result = stdout.decode('UTF-8').strip("\r\n")
                finally:
                    # timeout clear
                    timer_proc.cancel()

            # timeout check
            if self._timeout_occurred is True:
                # move the cursor to next line
                print("")
                raise TimeoutError
            return result

    t = Local()
    return t.input_timer_main(prompt, timeout_sec)


def input_w_timeout(str_to_print, timeout_sec=600, quit=True):
    try:
        title = input_timer(str_to_print, timeout_sec)
        return title
    except TimeoutError:
        print(f"\nno input for {timeout_sec / 60:.0f} minutes. program exited.")
        if quit:
            sys.exit()
        else:
            pass


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    My_Auto_Book_Record = AutoBookRecord()
