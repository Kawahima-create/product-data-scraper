"""
商品データ収集ツール（デモ版）
---------------------------------
Webサイトの商品一覧ページから「商品名・価格・評価・在庫状況」を収集し、
CSVファイルに保存します。

このデモはスクレイピング練習用に公開されているサイト
(books.toscrape.com) を対象にしています。
本番では、対象サイトの構造に合わせて抽出部分（parse_product）を
調整することで、どのECサイトにも応用できます。

使い方:
    python scraper.py                # 全ページ収集
    python scraper.py --pages 3      # 最初の3ページだけ収集
"""

import argparse
import csv
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# 収集対象サイト（スクレイピング学習用の公開サンドボックス）
BASE_URL = "https://books.toscrape.com/catalogue/"
START_PAGE = "page-1.html"

# 星評価の英単語 → 数値への変換表
RATING_MAP = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}

# サーバーに負荷をかけないためのリクエスト間隔（秒）
REQUEST_DELAY = 0.5


def fetch(url):
    """指定URLのHTMLを取得する。失敗時は例外を投げる。"""
    headers = {"User-Agent": "Mozilla/5.0 (product-data-demo)"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding
    return resp.text


def parse_product(article):
    """商品1件分のHTML要素から、必要な項目を辞書で抜き出す。

    ★本番ではこの関数を対象サイトに合わせて書き換える★
    """
    title = article.h3.a["title"].strip()

    price = article.select_one("p.price_color").get_text(strip=True)
    # 通貨記号などを除いて数値だけにする（"£51.77" -> 51.77）
    price_value = price.lstrip("£$¥").replace(",", "")

    rating_word = article.select_one("p.star-rating")["class"][1]
    rating = RATING_MAP.get(rating_word, "")

    stock = article.select_one("p.instock.availability").get_text(strip=True)
    in_stock = "在庫あり" if "In stock" in stock else "在庫なし"

    return {
        "商品名": title,
        "価格": price_value,
        "評価(星)": rating,
        "在庫": in_stock,
    }


def scrape(max_pages=None):
    """一覧ページをたどりながら全商品を収集してリストで返す。"""
    products = []
    next_page = START_PAGE
    page_count = 0

    while next_page:
        page_count += 1
        url = urljoin(BASE_URL, next_page)
        print(f"  {page_count}ページ目を取得中... ({url})")

        html = fetch(url)
        soup = BeautifulSoup(html, "html.parser")

        for article in soup.select("article.product_pod"):
            products.append(parse_product(article))

        # 「次へ」ボタンがあれば次ページURLを取得、なければ終了
        next_link = soup.select_one("li.next a")
        next_page = next_link["href"] if next_link else None

        if max_pages and page_count >= max_pages:
            break

        time.sleep(REQUEST_DELAY)  # 相手サーバーへの配慮

    return products


def save_csv(products, path="products.csv"):
    """収集結果をCSVに保存する（Excelで文字化けしないUTF-8 BOM付き）。"""
    if not products:
        print("収集結果がありません。")
        return
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(products[0].keys()))
        writer.writeheader()
        writer.writerows(products)
    print(f"\n✅ {len(products)}件を {path} に保存しました。")


def main():
    parser = argparse.ArgumentParser(description="商品データ収集デモ")
    parser.add_argument("--pages", type=int, default=None,
                        help="収集するページ数（省略時は全ページ）")
    parser.add_argument("--out", default="products.csv", help="出力CSVファイル名")
    args = parser.parse_args()

    print("商品データの収集を開始します...")
    products = scrape(max_pages=args.pages)
    save_csv(products, args.out)


if __name__ == "__main__":
    main()
