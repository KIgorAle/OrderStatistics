import psycopg2
from flask import Flask, render_template
from flask_table import Table, Col
import plotly.graph_objs as go
from plotly.subplots import make_subplots

app = Flask(__name__, template_folder='templates')

# Настройки соединения с базой данных
db_settings = {
    'dbname': 'mydb',
    'user': 'myuser',
    'password': '0000',
    'host': 'localhost',
    'port': 5432
}


# Создание функции для получения данных из базы данных
def get_data():
    # Создание соединения с базой данных
    conn = psycopg2.connect(**db_settings)

    # Создание курсора
    cur = conn.cursor()

    cur.execute("""SELECT *
                       FROM my_schema.mytable
                       ORDER BY num;""")
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return rows


# Определение класса для создания таблицы
class ItemTable(Table):
    num = Col('№')
    order_number = Col('Заказ №')
    price_usd = Col('Стоимость,$')
    price_rub = Col('Стоимость,Руб')
    delivery_date = Col('Срок поставки')


# Функция заполнения данных
def fill_data(page_created):
    rows = get_data()
    table = ItemTable([dict(zip(['num', 'order_number', 'price_usd', 'price_rub', 'delivery_date'], row)) for row in rows])

    # Получение списка стоимостей заказов в долларах и в рублях
    data = sorted(rows, key=lambda x: x[4])  # сортируем по дате поставки

    usd_prices_by_date = {}
    for row in data:
        date = row[4]
        price_usd = row[2]
        if date in usd_prices_by_date:
            usd_prices_by_date[date] += price_usd
        else:
            usd_prices_by_date[date] = price_usd

    usd_prices = list(usd_prices_by_date.values())
    delivery_date = list(usd_prices_by_date.keys())

    # Создание подграфиков
    fig = make_subplots(rows=1, cols=1)

    # Добавление графика стоимостей заказов в долларах
    fig.add_trace(
        go.Scatter(x=delivery_date, y=usd_prices, name='Стоимость,$', mode='lines'),
        row=1, col=1
    )

    # Настройка отображения графика
    fig.update_layout(title='Диаграмма прибыли',
                      xaxis_title='Дата поставки',
                      yaxis_title='Стоимость,$',
                      legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
                      plot_bgcolor='rgba(0,0,0,0)',  # убирает фон графика
                      paper_bgcolor='rgba(0,0,0,0)',  # убирает фон листа, на котором выводится график
                      hovermode='x',  # выделяет точку на графике по вертикальной линии
                      hoverdistance=1000,  # насколько далеко от вертикальной линии выводится точка на графике
                      spikedistance=1000,  # насколько далеко выводится линия, указывающая на ось
                      xaxis=dict(
                          tickformat="%d.%m.%Y"  # формат даты на оси x
                      )
                      )

    if page_created:
        # Создание словаря с обновленными данными
        data_dict = {
            'table': table,
            'graph': fig.to_html(full_html=False),
            'total_usd': sum([row[2] for row in rows]),
            'total_rub': sum([row[3] for row in rows])
        }
        return data_dict
    else:
        graph = fig.to_html(full_html=False)

        total_usd = sum([row[2] for row in rows])
        total_rub = sum([row[3] for row in rows])

        return render_template('index.html', table=table, graph=graph, total_usd=total_usd, total_rub=total_rub)


# Роут для заполнения страницы объектами с данными (график, таблица и т.д.)
@app.route('/')
def index():
    return fill_data(False)


# Роут для обновления данных на странице
@app.route('/update_data')
def update_data():
    return fill_data(True)


if __name__ == '__main__':
    app.run()