import requests
import csv
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ru,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://spbkoleso.ru/",
    "Upgrade-Insecure-Requests": "1",
}

def parse_mosautoshina(url):
    response = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(response.text, "html.parser")

    tyres = []
    items = soup.select("li.product.item")
    print(f"[mosautoshina] Найдено товаров: {len(items)}")

    for item in items:
        name_tag = item.select_one(".product-name")
        name = name_tag.text.strip() if name_tag else "Нет названия"

        price_tag = item.select_one(".product-price")
        price = price_tag.text.strip().replace("\u2009", "").replace("\xa0", "").replace("₽", "").strip() if price_tag else "Нет цены"

        image_tag = item.select_one(".product-image img")
        image_url = "https://mosautoshina.ru" + image_tag['src'] if image_tag else ""

        link_tag = item.select_one("a.product-container")
        link = "https://mosautoshina.ru" + link_tag['href'] if link_tag else ""

        country_tag = item.select_one(".product-country .country-name")
        country = country_tag.text.strip() if country_tag else ""

        season_icon = item.select_one(".badge-season")
        if season_icon:
            classes = season_icon.get("class", [])
            if "icon-summer" in classes:
                season = "Лето"
            elif "icon-winter" in classes:
                season = "Зима"
            elif "icon-all-season" in classes:
                season = "Всесезон"
            else:
                season = "Неизвестно"
        else:
            season = "Не указано"

        tyres.append({
            "Название": name,
            "Цена (₽)": price,
            "Сезон": season,
            "Страна": country,
            "Изображение": image_url,
            "Ссылка": link,
            "Источник": "mosautoshina.ru"
        })

    return tyres

def parse_spbkoleso(url):
    print(f"[spbkoleso] Парсинг: {url}")
    tyres = []

    # Настройка headless Chrome
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0")

    driver_path = os.path.join(os.getcwd(), "chromedriver.exe")
    service = Service(driver_path)

    # Запуск браузера
    driver = webdriver.Chrome(service=service, options=chrome_options)

    driver.get(url)

    SCROLL_PAUSE_TIME = 1.0
    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SCROLL_PAUSE_TIME)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "digi-product"))
        )
    except:
        print("⚠️ Карточки не загрузились.")
        driver.quit()
        return tyres

    # Получаем HTML и парсим через BeautifulSoup
    html = driver.page_source
    driver.quit()
    soup = BeautifulSoup(html, "html.parser")

    items = soup.select("div.digi-product")
    print(f"Найдено товаров: {len(items)}")

    for item in items:
        link_tag = item.select_one("a[href*='/shini/']")
        relative_link = link_tag['href'] if link_tag else ""
        full_link = "https://spbkoleso.ru" + relative_link if relative_link else ""

        brand = item.select_one(".digi-product__brand")
        model = item.select_one(".digi-product__label")
        name = f"{brand.text.strip()} {model.text.strip()}" if brand and model else "Нет названия"

        price_tag = item.select_one(".digi-product-price-variant_actual")
        price = price_tag.text.strip().replace("\xa0", "").replace("₽", "").replace(" ", "") if price_tag else "Нет цены"

        image_tag = item.select_one("img.digi-product__image")
        image_url = image_tag["src"] if image_tag else ""
        if image_url.startswith("//"):
            image_url = "https:" + image_url

        tyres.append({
            "Название": name,
            "Цена (₽)": price,
            "Сезон": "Не указано",
            "Страна": "Не указано",
            "Изображение": image_url,
            "Ссылка": full_link,
            "Источник": "spbkoleso.ru"
        })

    return tyres



def save_to_csv(data, filename="tyres.csv"):
    if not data:
        print("Нет данных для сохранения.")
        return
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)

def save_to_html(data, filename="tyres.html"):
    with open(filename, "w", encoding="utf-8") as f:
        f.write("""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Каталог шин</title>
    <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 8px; border: 1px solid #ccc; text-align: left; vertical-align: top; }
        img { max-height: 80px; }
        a.button { text-decoration: none; color: white; background: #2a9fd6; padding: 4px 8px; border-radius: 4px; }
    </style>
</head>
<body>
    <h2>Каталог шин по размеру 195/75 R16</h2>
    <table id="tyreTable">
        <thead>
            <tr>
                <th>Изображение</th>
                <th>Название</th>
                <th>Цена (₽)</th>
                <th>Сезон</th>
                <th>Страна</th>
                <th>Источник</th>
                <th>Ссылка</th>
            </tr>
        </thead>
        <tbody>
""")
        for tyre in data:
            f.write(f"""
            <tr>
                <td><img src="{tyre['Изображение']}" alt="img"></td>
                <td>{tyre['Название']}</td>
                <td>{tyre['Цена (₽)'].replace(" ", "")}</td>
                <td>{tyre['Сезон']}</td>
                <td>{tyre['Страна']}</td>
                <td>{tyre['Источник']}</td>
                <td><a href="{tyre['Ссылка']}" target="_blank" class="button">Перейти</a></td>
            </tr>
""")
        f.write("""
        </tbody>
    </table>

    <script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
    <script>
        $(document).ready(function() {
            $('#tyreTable').DataTable({
                "order": [[2, "asc"]],
                "language": {
                    "search": "Поиск:",
                    "lengthMenu": "Показать _MENU_ записей на странице",
                    "zeroRecords": "Ничего не найдено",
                    "info": "Показано с _START_ по _END_ из _TOTAL_ записей",
                    "infoEmpty": "Нет доступных записей",
                    "infoFiltered": "(отфильтровано из _MAX_ записей)",
                    "paginate": {
                        "first": "Первая",
                        "last": "Последняя",
                        "next": "Следующая",
                        "previous": "Предыдущая"
                    }
                },
                "columnDefs": [
                    { "type": "num", "targets": 2 }
                ]
            });
        });
    </script>
</body>
</html>
""")

# === Точка входа ===

if __name__ == "__main__":
    all_tyres = []

    # парсинг с mosautoshina
    # all_tyres.extend(parse_mosautoshina("https://mosautoshina.ru/catalog/tyre/search/by-size/-195-75-16------1-----/"))

    # парсинг с spbkoleso
    all_tyres.extend(parse_spbkoleso("https://spbkoleso.ru/?digiSearch=true&term=195%2F75%20R16C&params=%7Csort%3DDEFAULT"))

    # сохранить
    save_to_csv(all_tyres, "tyres_summary.csv")
    save_to_html(all_tyres, "tyres_summary.html")

    print(f"\nСохранено {len(all_tyres)} шин в: tyres_summary.csv и tyres_summary.html")
