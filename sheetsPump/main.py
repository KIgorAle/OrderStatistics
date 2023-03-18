from datetime import datetime
from datetime import date
from decimal import Decimal
from google.oauth2 import service_account
from googleapiclient.discovery import build
from bs4 import BeautifulSoup
import requests
import psycopg2
import time
import threading
import queue

# Класс для отправки уведомлений в Telegram
class TelegramNotifier(threading.Thread):
    def __init__(self):
        super().__init__()
        self.message_queue = queue.Queue()

    def run(self):
        while True:
            message = self.message_queue.get()
            url = f'https://api.telegram.org/bot6130082234:AAGJTu9Wf6igFxh4o_ga0I5B_i7jGzL_53I/sendMessage?chat_id=652267536&text={message}'
            response = requests.get(url)
            if response.status_code == 200:
                print(f'Telegram уведомление отправлено: {message}')
            else:
                print(f'Ошибка при отправке Telegram уведомления: {response.content}')
            self.message_queue.task_done()


# Функция заполнения пустой базы данных
def fill_empty_db_table(sheet_data, currency, conn, notifier):
    cursor = conn.cursor()

    # получение данных из таблицы и добавление в БД
    for row in sheet_data[1:]:  # пропускаем заголовок таблицы

        # пропускаем строку в случае, если номер, номер заказа, стоимость в $ не соответствует числу
        # (пустая строка, текст и прочее) или если срок поставки не соответствует дате
        if not row[0].isdigit() or not row[1].isdigit() or not row[2].isdigit():
            continue

        # пропускаем строку в случае если срок поставки не соответствует дате
        if len(row) < 4:
            continue
        else:
            if not check_date(row[3]):
                continue

        num = int(row[0])
        order_num = int(row[1])
        price = Decimal(row[2]).quantize(Decimal('0.01'))

        # перевод цены в рубли
        rub_price = float(price) * float(currency.replace(',', '.'))
        rub_price = Decimal(str(rub_price)).quantize(Decimal('0.01'))
        delivery_date = datetime.strptime(row[3], '%d.%m.%Y').date()

        # Проверка, прошла ли дата доставки, и отправка уведомления в Telegram, если это так
        if delivery_date < date.today():
            message = f"Заказ {num} уже должен был быть доставлен"
            notifier.message_queue.put(message)

        # добавление записи в БД
        cursor.execute("""
            INSERT INTO my_schema.mytable (num, order_num, price, rub_price, delivery_date)
            VALUES (%s, %s, %s, %s, %s)
        """, (num, order_num, price, rub_price, delivery_date))
        conn.commit()


# Функция сравнения кортежей таблицы и БД, с последующим обновлением БД
def db_updater(db_data, gs_data, conn, notifier):
    cursor = conn.cursor()

    counter = {"updated": 0, "added": 0, "deleted": 0}

    # сравнение списков данных
    for gs_row in gs_data:
        # поиск соответствующей записи в базе данных
        match = None
        for db_row in db_data:
            if gs_row[0] == db_row[0]:
                match = db_row
                break

        # если запись найдена и данные изменились, то обновляем запись в базе данных
        if match and gs_row != match:
            cursor.execute(
                "UPDATE my_schema.mytable SET order_num = %s, price = %s, rub_price = %s, delivery_date = %s WHERE num = %s;",
                (gs_row[1], gs_row[2], gs_row[3], gs_row[4], gs_row[0]))
            counter["updated"] += 1

            # если delivery date изменилась и эта дата уже прошла - отправляем уведомление
            if gs_row[4] != match[4] and gs_row[4] < date.today():
                message = f"Заказ {gs_row[0]} уже должен был быть доставлен"
                notifier.message_queue.put(message)

        # если запись не найдена, то добавляем запись в базу данных
        elif not match:
            cursor.execute(
                "INSERT INTO my_schema.mytable (num, order_num, price, rub_price, delivery_date) VALUES (%s, %s, %s, %s, %s);",
                (gs_row[0], gs_row[1], gs_row[2], gs_row[3],
                 gs_row[4]))
            counter["added"] += 1
            # Проверка, прошла ли дата доставки, и отправка уведомления в Telegram, если это так
            if gs_row[4] < date.today():
                message = f"Заказ {gs_row[0]} уже должен был быть доставлен"
                notifier.message_queue.put(message)

    # удаление записей, которые были удалены в таблице Google Sheets
    for db_row in db_data:
        match = False
        for gs_row in gs_data:
            if gs_row[0] == db_row[0]:
                match = True
                break
        if not match:
            cursor.execute("DELETE FROM my_schema.mytable WHERE num = %s;", (db_row[0],))
            counter["deleted"] += 1

    conn.commit()

    if counter["updated"] > 0 or counter["added"] > 0 or counter["deleted"]:
        print('Data has been Updated. Row(s): Updated: ' + str(counter["updated"]) + ', Added: ' + str(
            counter["added"]) + ', Deleted: ' + str(counter["deleted"]))
    else:
        print('No updates.')

    return None


# Функция получения листа таблицы в Google Sheets
def get_sheet():
    # авторизация через JSON-ключ
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive.readonly']
    SERVICE_ACCOUNT_FILE = 'Credentials/ordersproject-380812-b3fab659dc9a.json'
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)

    # получение таблицы по ID
    SPREADSHEET_ID = '1y9WCh_0dq7hEXgcLD9dI-M3zr8Oti4hsogFfNA0TTlE'
    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range='Лист1').execute()
    return sheet.get('values')


# Функция получения курса валюты
def get_currency():
    url = 'https://www.cbr.ru/scripts/XML_daily.asp'
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'xml')
    return soup.find('CharCode', string='USD').find_next_sibling('Value').string


# Функция проверки существования таблицы в БД
def table_exists(cursor):
    cursor.execute("SELECT EXISTS(SELECT * FROM information_schema.tables WHERE table_name = 'mytable')")
    return cursor.fetchone()[0]


# Функция создания таблицы в БД
def table_create(conn):
    # создание новой схемы
    cursor = conn.cursor()
    cursor.execute("CREATE SCHEMA IF NOT EXISTS my_schema;")
    conn.commit()

    # создание таблицы в новой схеме
    cursor.execute("""
        CREATE TABLE my_schema.mytable (
            num SERIAL PRIMARY KEY,
            order_num INTEGER NOT NULL,
            price NUMERIC(10, 2) NOT NULL,
            rub_price NUMERIC(10, 2) NOT NULL,
            delivery_date DATE NOT NULL
        )
    """)
    conn.commit()
    return None


# Функция сохранения данных БД в кортеж
def db_data_to_tuple(rows):
    db_data = []
    for row in rows:
        db_data.append((row[0], row[1], row[2], row[3], row[4]))
    return db_data


# Функция сохранения данных листа в кортеж
def sheet_data_to_tuple(sheet_data, currency):
    gs_data = []
    for row in sheet_data[1:]:

        # пропускаем строку в случае, если номер, номер заказа, стоимость в $ не соответствует числу
        # (пустая строка, текст и прочее) или если срок поставки не соответствует дате
        if not row[0].isdigit() or not row[1].isdigit() or not row[2].isdigit():
            continue

        # пропускаем строку в случае если срок поставки не соответствует дате
        if len(row) < 4:
            continue
        else:
            if not check_date(row[3]):
                continue

        # перевод цены в рубли
        rub_price = float(row[2]) * float(currency.replace(',', '.'))

        # Преобразование типов данных
        gs_data.append((int(row[0]), int(row[1]), Decimal(row[2]).quantize(Decimal('0.01')),
                        Decimal(str(rub_price)).quantize(Decimal('0.01')),
                        datetime.strptime(row[3], '%d.%m.%Y').date()))
    return gs_data


# Функция получения и вывода данных из базы данных
def display_data(cursor):
    cursor.execute("""SELECT *
                       FROM my_schema.mytable
                       ORDER BY num;""")
    rows = cursor.fetchall()

    # for row in rows:
    #     print(row)
    return rows


# Функция проверки валидности даты
def check_date(date):
    date_format = '%d.%m.%Y'
    try:
        delivery_date = datetime.strptime(date, date_format).date()
        return True
    except ValueError:
        print(f"Invalid date format for value {date}. Expected format: {date_format}")
        return False


# Главная функция скрипта
def main():

    # запуск нотификатора
    notifier = TelegramNotifier()
    notifier.start()

    # вечный цикл для постоянной работы скрипта
    while True:
        # получение курса валюты
        currency = get_currency()

        # получение данных из таблицы в Google Sheets
        sheet_data = get_sheet()

        # вывод данных в консоль
        # print(sheet_data)

        # подключение к БД
        conn = psycopg2.connect(host='localhost', port=5432, database='mydb', user='myuser', password='0000')
        cursor = conn.cursor()

        # проверка существования таблицы в БД
        if not table_exists(cursor):

            # создание таблицы в БД
            table_create(conn)

            # заполнение таблицы
            fill_empty_db_table(sheet_data, currency, conn, notifier)

            display_data(cursor)

            # закрытие подключения к БД
            cursor.close()
            conn.close()

            print('Data has been filled.')

        else:
            rows = display_data(cursor)

            # заполнение списков
            db_data = db_data_to_tuple(rows)
            gs_data = sheet_data_to_tuple(sheet_data, currency)

            # сравниение списков и обновление базы данных
            db_updater(db_data, gs_data, conn, notifier)

            # закрытие подключения к БД
            cursor.close()
            conn.close()

        # 30 секундная (для удобства проверки) пауза перед следующим выполнением проверки и обновления данных
        time.sleep(30)


# Запускаем скрипт
if __name__ == '__main__':
    main()