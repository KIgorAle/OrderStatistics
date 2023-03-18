# OrderStatistics.

Проект состоит из двух скриптов:
1. sheetsPump/main.py - Python скрипт который выполняет следующие функции:

	1. Получает данные из документа (таблицы/листа), сделанного в Google Sheets, при помощи Google API.
	2. Данные добавляются в БД, с добавлением колонки «Стоимость,Руб»

		  a. БД на основе PostgreSQL.

		  b. Данные для перевода $ в рубли получаются по курсу ЦБ РФ.

	3. Скрипт работает постоянно для обеспечения обновления данных в онлайн режиме (учитывает, что строки в Google Sheets таблице могут удаляться, добавляться и изменяться). Проверка данных листа происходит каждые 30 секунд после завершения предыдущей проверки (и обновления) данных. При сравнении данных листа и таблицы БД для хранения используются кортежи.

	4. В скрипте присутствует функционал проверки соблюдения «срока поставки» из таблицы. В случае, если срок прошел - скрипт отправляет уведомление в Telegram. Отправка уведомлений выведена в отдельный тред дабы не тормозить основной процесс.

2.  FlaskServer/main.py - одностраничное web-приложение на основе Flask, подключающееся к БД и отображающее таблицу, график и общую прибыль в долларах и рублях. Данные обновляются каждые 5 секунд без перезагрузки страницы. Для отоброжения графика используется Plotly.


# Инструкция:
1. В PyCharm 2021.1 (Community Edition) создаются 2 проекта называнные так же как папки из данного репозитория, в них добавляются все файлы и папки из одноимённых папок репозитория. С помощью подсказок PyCharm устанавливаются все недостающие импорты (подчёркнутые красным и мешающие нормальному запуску скриптов). Возможно в терминале первого проекта потребуется ввести pip install xml (в случае ошибки связанной с xml).
2. Поднимаем PostgreSQL (в данном случае на Windows 10):
	1. Скачиваем установочный файл PostgreSQL с официального сайта по ссылке https://www.postgresql.org/download/windows/.
	2. Запускаем установку PostgreSQL, следуя инструкциям на экране.
	3. Задаём пароль суперпользователю оба раза: 1234
	3. При установке выбираем опцию "PostgreSQL Server" и выбираем порт 5432.
	4. Запускаем PostgreSQL Server, используя службу "PostgreSQL" в меню служб Windows.
	5. Запускаем от имени администратора pgAdmin 4, создаём там базу данных с именем mydb (Databases -> Create -> Database).
	6. Создаём пользователя БД с именем myuser и паролем 0000 (Login/Group Roles -> Create -> Login/Group Role), выдаём ему все привилегии (Privileges), в разделе Membership в "Member of" добавляем "pg_read_all_data" и "pg_write_all_data" и ставим напротив них галочки (WITH ADMIN), сохраняем.
3. В коде sheetsPump/main.py в строке "https://api.telegram.org/bot6130082234:AAGJTu9Wf6igFxh4o_ga0I5B_i7jGzL_53I/sendMessage?chat_id=652267536&text={message}" заменяем chat_id (652267536) на свой Telegram id (узнать его можно через бота https://t.me/get_id_bot), туда будут приходить вам Telegram уведомления.
4. Заходим в свой Telegram аккаунт, открываем бота https://t.me/Orders_Notifications_bot, запускаем его (/start), от него вам будут приходить уведомления.
5. Запускаем sheetsPump/main.py, ждём от него сообщение "Data has been filled." (при первом запуске, когда таблица ещё на создана в БД и не заполнена, далее вас ожидают надписи "No updates." и "Data has been Updated. Row(s): Updated: X, Added: Y, Deleted: Z"). Запускаем FlaskServer/main.py.
6. Открываем в своём браузере адрес: http://127.0.0.1:5000/
7. Смотрим график, смотрим таблицу, редактируем лист в Google Sheets, смотрим как SheetsPump обновляет данные в БД, шлёт уведомления на телеграм, и смотрим как FlaskServer берёт эти данные из БД, отрисовывает график, заполняет таблицу, обновляет их.
8. Ссылка на таблицу Google Sheets используемую в проекте: https://docs.google.com/spreadsheets/d/1y9WCh_0dq7hEXgcLD9dI-M3zr8Oti4hsogFfNA0TTlE/edit#gid=0
