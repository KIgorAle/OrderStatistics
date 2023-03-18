# OrderStatistics

Проект состоит из двух скриптов:
1) sheetsPump/main.py - Python скрипт который выполняет следующие функции:

  1. Получает данные с документа (таблицы/листа), сделанного в Google Sheets, при помощи Google API.
  2. Данные должны добавляются в БД, с добавлением колонки «Стоимость,Руб»

      a. БД на основе PostgreSQL.

      b. Данные для перевода $ в рубли необходимо получаются по курсу ЦБ РФ.

  3. Скрипт работает постоянно для обеспечения обновления данных в онлайн режиме (учитывает, что строки в Google Sheets таблице могут удаляться, добавляться и изменяться).
  Проверка данных листа происходит каждые 30 секунд после завершения предыдущей проверки (и обновления) данных.
  При сравнении данных листа и таблицы БД для хранения используются кортежи.

  4. В скрипте присутствует функционал проверки соблюдения «срока поставки» из таблицы. В случае, если срок прошел, скрипт отправляет уведомление в Telegram.
  Отправка уведомлений выведена в отдельный тред дабы не тормозить основной процесс.

2) Одностраничное web-приложение на основе Flask подключающееся к БД и отображающее таблицу, график и общую прибыль в долларах и рублях.
Данные обновляются каждые 5 секунд без перезагрузки страницы. Для отоброжения графика используется Plotly.
