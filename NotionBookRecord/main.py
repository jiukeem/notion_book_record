import sys
import requests
import json
from datetime import datetime


class AutoBookRecord:
    def __init__(self):
        self.aladin = Aladin()
        self.notion = Notion()
        self.book = None
        self.timeout_sec = 600
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
        title = input_w_timeout('\nplease enter book title: ', self.timeout_sec)
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
        chosen_book_index_str = input_w_timeout('Please enter the number of the book you want to add: ', self.timeout_sec)
        # ------------------------ printed for user ------------------------

        chosen_book_index_num = 0
        while chosen_book_index_num < 1:
            if chosen_book_index_str == 'b':
                self.reset()
                return

            if chosen_book_index_str in list(map(str, range(1, len(candidate_book_list) + 1))):
                chosen_book_index_num = int(chosen_book_index_str)
            else:
                chosen_book_index_str = input_w_timeout(f'Enter proper number(1 ~ {len(candidate_book_list)}) only: ',
                                                        self.timeout_sec)

        return chosen_book_index_num - 1

    def request_book_info(self, title):
        params = {'TTBKey': self.aladin.ttb_key, 'Query': title, 'Output': 'JS', 'Version': 20131101, 'Cover': 'Big'}
        response = requests.get(url=self.aladin.request_url, params=params)
        return response

    def trim_response_to_json(self, raw_response):
        return json.loads(raw_response.text)['item']

    def set_book_configuration(self, book):
        b = book
        aladin_category = self.parse_category(b['categoryName'])
        category = self.get_correspondence_kyobo_category(aladin_category)
        p = self.parse_author_w_translator(b['author'])
        authors = p['authors']
        translator = p['translator']

        self.book = Book(
            title=b['title'],
            author=authors,
            publisher=b['publisher'],
            translator=translator,
            image=b['cover'],
            info_url=b['link'],
            category=category
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

        return {'authors': ', '.join(author_list), 'translator': default_translator}

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
        return {"title": {"title": [{"text": {"content": self.book.title}}]},
                "대분류": {"select": {"name": self.book.category}},
                "지은이": {"rich_text": [{"type": "text", "text": {"content": self.book.author}}]},
                "출판사": {"rich_text": [{"type": "text", "text": {"content": self.book.publisher}}]},
                "옮긴이": {"rich_text": [{"type": "text", "text": {"content": self.book.translator}}]},
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

    def get_correspondence_kyobo_category(self, category):
        aladin_to_kyobo = {'요리/살림': '기타',
                           '건강/취미': '기타',
                           '경제경영': '경제/경영',
                           '고전': '기타',
                           '과학': '과학',
                           '달력/기타': '기타',
                           '대학교재': '기타',
                           '만화': '기타',
                           '사회과학': '정치/사회',
                           '소설/시/희곡': '소설',
                           '에세이': '에세이',
                           '수험서/자격증': '기타',
                           '공무원 수험서': '기타',
                           '어린이': '기타',
                           '유아': '기타',
                           '여행': '기타',
                           '역사': '역사/문화',
                           '예술/대중문화': '예술/대중문화',
                           '외국어': '외국어',
                           '인문학': '인문',
                           '자기계발': '자기계발',
                           '잡지': '잡지',
                           '장르소설': '소설',
                           '전집/중고전집': '기타',
                           '종교/역학': '종교',
                           '좋은부모': '기타',
                           '청소년': '기타',
                           '초등참고서': '기타',
                           '중학교참고서': '기타',
                           '고등학교참고서': '기타',
                           '컴퓨터/모바일': '컴퓨터/IT',
                           }
        try:
            return aladin_to_kyobo[category]
        except KeyError:
            return '알 수 없음'


class Book:
    def __init__(self, title, author, publisher, translator, image, info_url, category):
        self.title = title
        self.author = author
        self.publisher = publisher
        self.translator = translator
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


# https://greenfishblog.tistory.com/257
def input_timer(prompt, timeout_sec):
    import subprocess
    import sys
    import threading
    import locale

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


def input_w_timeout(str_to_print, timeout_sec, quit=True):
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
