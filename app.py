import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import numpy as np

st.set_page_config(layout="wide") 



def load_excel():
    uploaded_file = st.file_uploader("📂 Загрузите Excel файл", type=["xlsx"])
    if uploaded_file is not None:
        try:
            raw_df = pd.read_excel(uploaded_file, header=None)  
            st.write("Превью данных:")
            st.write(raw_df.head(10))  

           
            header_row = st.number_input(
                "Укажите строку, где находятся заголовки (0 = первая строка)",
                min_value=0, max_value=len(raw_df) - 1, value=0, step=1)
            df = pd.read_excel(uploaded_file, header=header_row)

           
            df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
            st.success("Файл успешно загружен!")
            st.write("Колонки в файле:", df.columns.tolist()) 
            st.write(df.head())  
            return df
        except Exception as e:
            st.error(f"Ошибка загрузки файла: {e}")
    return None



def auto_detect_columns(df):
    mapping = {
        "ИП": ["ИП", "Магазин", "Компания"],
        "Себестоимость": ["С/с", "Себестоимость", "Себестоимость, ₽"],
        "Базовая цена": ["Базовая цена", "Цена продажи", "Продажная цена", "Базовая, ₽"],
        "Продажа шт": ["Продажа шт", "Количество", "Кол-во", "Заказы", "Заказы Количество, шт."],
        "Товар": ["Товар", "Наименование", "Продукт", "Название"],
        "Категория": ["Категория", "Группа товаров", "Тип товара"]  
    }
    detected_columns = {}
    for key, possible_names in mapping.items():
        for name in possible_names:
            if name in df.columns:
                detected_columns[key] = name
                break
    return detected_columns



def calculate_metrics(df, columns):
    metrics_by_ip = {}
    try:
        grouped = df.groupby(columns["ИП"])
        for ip, group in grouped:
            metrics = {}
            
            if "Себестоимость" in columns and "Базовая цена" in columns and "Продажа шт" in columns:
                group["Маржа"] = (pd.to_numeric(group[columns["Базовая цена"]], errors="coerce") - pd.to_numeric(
                    group[columns["Себестоимость"]], errors="coerce")) * pd.to_numeric(group[columns["Продажа шт"]],
                                                                                       errors="coerce")
                metrics["Общая маржа"] = round(group["Маржа"].sum(), 2)

            
            if "Базовая цена" in columns and "Продажа шт" in columns:
                group["Сумма продаж"] = pd.to_numeric(group[columns["Базовая цена"]], errors="coerce") * pd.to_numeric(
                    group[columns["Продажа шт"]], errors="coerce")
                metrics["Сумма продаж"] = int(group["Сумма продаж"].sum())

            
            if "Продажа шт" in columns:
                metrics["Количество заказов"] = int(pd.to_numeric(group[columns["Продажа шт"]], errors="coerce").sum())

            
            if "Сумма продаж" in group.columns and "Продажа шт" in columns:
                total_orders = metrics["Количество заказов"]
                metrics["Средний чек"] = round(metrics["Сумма продаж"] / total_orders, 2) if total_orders > 0 else 0

            metrics_by_ip[ip] = metrics
    except Exception as e:
        st.error(f"Ошибка при расчете метрик для ИП: {e}")
    return metrics_by_ip



def plot_category_sales(df, columns, ip_name):
    
    if "Категория" not in columns or "Сумма продаж" not in columns:
        st.warning(f"Данные для построения графика отсутствуют для ИП {ip_name}. Пропускаем.")
        return

    
    ip_df = df[df[columns["ИП"]] == ip_name]

    
    if ip_df.empty:
        st.warning(f"Нет данных для ИП {ip_name}. Пропускаем.")
        return

   
    if columns["Сумма продаж"] not in ip_df.columns or columns["Категория"] not in ip_df.columns:
        st.warning(f"Не хватает данных по категории или сумме продаж для ИП {ip_name}. Пропускаем.")
        return

    
    category_sales = ip_df.groupby(columns["Категория"])[columns["Сумма продаж"]].sum()

    
    if category_sales.empty or category_sales.sum() == 0:
        st.warning(f"Нет данных для построения графика для ИП {ip_name}. Пропускаем.")
        return

    
    st.subheader(f"Продажи по категориям для {ip_name}")
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = category_sales.sort_values(ascending=False).plot(kind="bar", ax=ax, color="skyblue")
    plt.ylabel("Сумма продаж (₽)")
    ax.yaxis.set_major_formatter(FuncFormatter(format_number))
    plt.grid(axis="y", linestyle="--", alpha=0.7)
    plt.xticks(rotation=45)

  
    for bar, value in zip(ax.patches, category_sales.sort_values(ascending=False)):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{int(value):,}".replace(",", " "),
            ha="center",
            va="bottom",
            fontsize=10
        )

    st.pyplot(fig)



def format_number(x, _):
    return f"{int(x):,}".replace(",", " ")



def compare_ips(metrics_by_ip, comparison_metric, selected_ips):
    data = {ip: metrics[comparison_metric] for ip, metrics in metrics_by_ip.items() if ip in selected_ips}
    labels = list(data.keys())
    values = list(data.values())

    #
    if not values or sum(values) == 0:
        st.warning("Нет данных для построения круговой диаграммы. Проверьте выбранные метрики и ИП.")
        return

    
    def autopct_generator(values):
        def autopct(pct):
            absolute = int(round(pct / 100. * sum(values)))
            return f"{pct:.1f}% ({absolute})"

        return autopct

    
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.pie(values, labels=labels, autopct=autopct_generator(values), startangle=140, colors=plt.cm.tab20c.colors)
    ax.axis('equal')  
    st.pyplot(fig)



df = load_excel()

if df is not None:
    
    detected_columns = auto_detect_columns(df)
    st.write("Автоматически определенные колонки:", detected_columns)

    
    for key in ["ИП", "Себестоимость", "Базовая цена", "Продажа шт", "Товар", "Категория"]:
        if key not in detected_columns:
            detected_columns[key] = st.selectbox(f"Выберите колонку для '{key}'", df.columns)

    
    if "Сумма продаж" not in detected_columns:
        if "Базовая цена" in detected_columns and "Продажа шт" in detected_columns:
            df["Сумма продаж"] = pd.to_numeric(df[detected_columns["Базовая цена"]], errors="coerce") * pd.to_numeric(
                df[detected_columns["Продажа шт"]], errors="coerce")
            detected_columns["Сумма продаж"] = "Сумма продаж"

    
    metrics_by_ip = calculate_metrics(df, detected_columns)
    st.subheader("Метрики по ИП")
    for ip, metrics in metrics_by_ip.items():
        with st.expander(f"Метрики для ИП: {ip}"):
            st.write(metrics)
            plot_category_sales(df, detected_columns, ip)

    
    st.subheader("Сравнение ИП")
    if "comparison_metric" not in st.session_state:
        st.session_state.comparison_metric = "Сумма продаж"

    if "selected_ips" not in st.session_state:
        st.session_state.selected_ips = list(metrics_by_ip.keys())

    valid_ips = list(metrics_by_ip.keys())
    st.session_state.selected_ips = [ip for ip in st.session_state.selected_ips if ip in valid_ips]

    st.session_state.comparison_metric = st.selectbox(
        "Выберите метрику для сравнения",
        ["Сумма продаж", "Общая маржа", "Количество заказов", "Средний чек"],
        index=["Сумма продаж", "Общая маржа", "Количество заказов", "Средний чек"].index(
            st.session_state.comparison_metric)
    )

    st.session_state.selected_ips = st.multiselect(
        "Выберите ИП для сравнения",
        options=valid_ips,
        default=st.session_state.selected_ips
    )

    if st.session_state.selected_ips:
        compare_ips(metrics_by_ip, st.session_state.comparison_metric, st.session_state.selected_ips)
