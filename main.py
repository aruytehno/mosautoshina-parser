import requests
from bs4 import BeautifulSoup
import csv

URL = "https://mosautoshina.ru/catalog/tyre/search/by-size/-195-75-16------1-----/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
}

def parse_page(url):
    response = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(response.text, "html.parser")

    tyres = []
    items = soup.select("li.product.item")

    print(f"Найдено товаров: {len(items)}")

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
            if "icon-summer" in season_icon["class"]:
                season = "Лето"
            elif "icon-winter" in season_icon["class"]:
                season = "Зима"
            elif "icon-all-season" in season_icon["class"]:
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
            "Ссылка": link
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

if __name__ == "__main__":
    tyres = parse_page(URL)
    save_to_csv(tyres)
    print(f"Сохранено {len(tyres)} шин в файл tyres.csv")
