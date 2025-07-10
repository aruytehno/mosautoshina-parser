import requests
import csv
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.actions.wheel_input import ScrollOrigin
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from selenium.webdriver.common.action_chains import ActionChains

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
    print(f"[spbkoleso] Начинается парсинг: {url}")
    tyres = []

    chrome_options = Options()
    # chrome_options.add_argument("--headless=new")  # Можно раскомментировать для отладки
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0")

    driver_path = os.path.join(os.getcwd(), "chromedriver.exe")
    service = Service(driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_window_size(1280, 1024)
    driver.get(url)

    wait = WebDriverWait(driver, 10)

    print("[spbkoleso] Ожидание контейнера с карточками...")
    container = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "digi-products-grid")))
    print("[spbkoleso] Контейнер загружен.")

    # --- НАЧАЛО БЛОКА СКРОЛЛИНГА ПО КОНТЕЙНЕРУ ---
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.webdriver.common.actions.wheel_input import ScrollOrigin

    # Инициализация ActionChains один раз
    actions = ActionChains(driver)
    origin = ScrollOrigin.from_element(container)

    scroll_pause = 1.0
    same_count_times = 0
    max_same_count_times = 10
    last_count = 0
    max_total_scrolls = 50  # ограничение, чтобы не зациклиться
    scrolls_done = 0

    while same_count_times < max_same_count_times and scrolls_done < max_total_scrolls:
        actions.move_to_element(container).perform()
        actions.scroll_from_origin(origin, 0, 500).perform()
        print("[scroll] Скролл колесиком выполнен на 500px")
        scrolls_done += 1

        time.sleep(scroll_pause)

        # Ожидаем либо новых товаров, либо таймаут
        try:
            WebDriverWait(driver, 2).until(
                lambda d: len(d.find_elements(By.CLASS_NAME, "digi-product")) > last_count
            )
        except Exception:
            pass  # если timeout — продолжаем

        products = driver.find_elements(By.CLASS_NAME, "digi-product")
        current_count = len(products)
        print(f"[scroll] Обнаружено товаров: {current_count}")

        if current_count > last_count:
            print(f"[scroll] Новые товары подгружены: {current_count - last_count}")
            last_count = current_count
            same_count_times = 0
        else:
            same_count_times += 1
            print(f"[scroll] Новых товаров нет. Попытка {same_count_times}/{max_same_count_times}")

    # --- КОНЕЦ БЛОКА СКРОЛЛИНГА ---

    html = driver.page_source
    driver.quit()

    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("div.digi-product")
    print(f"[spbkoleso] Всего найдено товаров: {len(items)}")

    for index, item in enumerate(items):
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

        print(f"[spbkoleso] Товар {index + 1}: {name}, Цена: {price}, Ссылка: {full_link}")

    print(f"[spbkoleso] Парсинг завершен. Найдено {len(tyres)} товаров.")
    return tyres




def parse_yandex_prices(url):
    print(f"[yandex] Начинается парсинг: {url}")
    results = []

    chrome_options = Options()
    # chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0")

    driver_path = os.path.join(os.getcwd(), "chromedriver.exe")
    service = Service(driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.set_window_size(1280, 1024)
    driver.get(url)

    wait = WebDriverWait(driver, 10)
    print("[yandex] Ожидание блока с товарами...")

    container = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "EShopList")))
    print("[yandex] Блок с товарами найден.")

    # --- Скроллинг ---
    actions = ActionChains(driver)
    origin = ScrollOrigin.from_element(container)

    scroll_pause = 1.0
    last_count = 0
    same_count_times = 0
    max_same_count_times = 8
    max_total_scrolls = 40
    scrolls_done = 0

    while same_count_times < max_same_count_times and scrolls_done < max_total_scrolls:
        actions.move_to_element(container).perform()
        actions.scroll_from_origin(origin, 0, 700).perform()
        print("[scroll] Скролл колесиком выполнен на 700px")
        scrolls_done += 1
        time.sleep(scroll_pause)

        products = driver.find_elements(By.CSS_SELECTOR, "li.EShopItem")
        current_count = len(products)
        print(f"[scroll] Найдено товаров: {current_count}")

        if current_count > last_count:
            same_count_times = 0
            last_count = current_count
        else:
            same_count_times += 1
            print(f"[scroll] Новых товаров нет. Попытка {same_count_times}/{max_same_count_times}")

    html = driver.page_source
    driver.quit()

    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("li.EShopItem")
    print(f"[yandex] Всего найдено карточек: {len(items)}")

    for idx, item in enumerate(items):
        name_tag = item.select_one(".EShopItem-Title")
        price_tag = item.select_one(".EPrice-Value")
        link_tag = item.select_one("a.Link[href]")

        name = name_tag.text.strip() if name_tag else "Нет названия"
        price = price_tag.text.strip().replace("\xa0", "") if price_tag else "Нет цены"
        link = link_tag['href'] if link_tag else ""

        shop_tag = item.select_one(".EShopName")
        shop = shop_tag.text.strip() if shop_tag else "Неизвестный магазин"

        image_tag = item.select_one("img.EThumb-Image")
        image_url = "https:" + image_tag['src'] if image_tag and image_tag['src'].startswith("//") else ""

        results.append({
            "Название": name,
            "Цена (₽)": price,
            "Магазин": shop,
            "Ссылка": link,
            "Изображение": image_url,
            "Источник": "yandex.ru"
        })

        print(f"[yandex] {idx + 1}. {name} — {price} ₽ — {shop} — {link}")

    print(f"[yandex] Парсинг завершён. Найдено {len(results)} товаров.")
    return results



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
    # all_tyres.extend(parse_spbkoleso("https://spbkoleso.ru/?digiSearch=true&term=195%2F75%20R16C&params=%7Csort%3DDEFAULT"))

    all_tyres.extend(parse_yandex_prices(
        "https://yandex.ru/search?text=Кама+Евро+131+195%2F75+R16C+107R&lr=2&promo=products_mode&serp-reload-from=product-sorts&goods_how=aprice"))

    # сохранить
    save_to_csv(all_tyres, "tyres_summary.csv")
    save_to_html(all_tyres, "tyres_summary.html")

    print(f"\nСохранено {len(all_tyres)} шин в: tyres_summary.csv и tyres_summary.html")
