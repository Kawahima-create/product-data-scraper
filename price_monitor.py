"""
価格モニタリングツール（上位プラン用）
---------------------------------------
前回収集した価格と今回を比較し、「値上げ・値下げ・新商品・販売終了」を
自動で検知してレポートします。

毎日 / 毎週など定期実行と組み合わせれば、
「競合の価格が動いたら気づける」仕組みになります。
（scraper.py の収集機能をそのまま再利用しています）

使い方:
    python price_monitor.py        # 収集 → 前回と比較 → 変動をレポート
"""

import csv
import os
from datetime import datetime

from scraper import scrape  # 既存の収集機能を再利用

SNAPSHOT_FILE = "price_snapshot.csv"   # 前回の価格を覚えておくファイル
CHANGES_FILE = "price_changes.csv"     # 変動内容の出力ファイル


def load_snapshot(path):
    """前回の価格スナップショットを {商品名: 価格} で読み込む。無ければ空。"""
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8-sig") as f:
        snapshot = {}
        for row in csv.DictReader(f):
            try:
                snapshot[row["商品名"]] = float(row["価格"])
            except (ValueError, KeyError):
                continue
        return snapshot


def save_snapshot(products, path):
    """今回の価格を次回比較用に保存する。"""
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["商品名", "価格"])
        writer.writeheader()
        for p in products:
            writer.writerow({"商品名": p["商品名"], "価格": p["価格"]})


def compare(old_prices, products):
    """前回と今回を比較し、変動のリストを返す。"""
    changes = []
    current_names = set()

    for p in products:
        name = p["商品名"]
        current_names.add(name)
        try:
            new_price = float(p["価格"])
        except ValueError:
            continue

        if name not in old_prices:
            changes.append((name, "🆕 新商品", "", new_price))
        elif old_prices[name] != new_price:
            diff = new_price - old_prices[name]
            kind = "🔺 値上げ" if diff > 0 else "🔻 値下げ"
            changes.append((name, kind, old_prices[name], new_price))

    # 前回あったのに今回消えた商品 = 販売終了
    for name, old_price in old_prices.items():
        if name not in current_names:
            changes.append((name, "❌ 販売終了", old_price, ""))

    return changes


def report(changes):
    """変動を画面に表示し、CSVにも保存する。"""
    if not changes:
        print("\n価格の変動はありませんでした。")
        return

    print(f"\n=== 価格変動レポート（{datetime.now():%Y-%m-%d %H:%M}）===")
    for name, kind, old_p, new_p in changes:
        old_str = f"{old_p:.2f}" if old_p != "" else "―"
        new_str = f"{new_p:.2f}" if new_p != "" else "―"
        print(f"  {kind}  {name}  ({old_str} → {new_str})")

    with open(CHANGES_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["商品名", "変動", "前回価格", "今回価格", "検知日時"])
        stamp = f"{datetime.now():%Y-%m-%d %H:%M}"
        for name, kind, old_p, new_p in changes:
            writer.writerow([name, kind, old_p, new_p, stamp])
    print(f"\n✅ {len(changes)}件の変動を {CHANGES_FILE} に保存しました。")


def main():
    print("価格モニタリングを開始します...")
    products = scrape(max_pages=2)

    old_prices = load_snapshot(SNAPSHOT_FILE)
    if not old_prices:
        print("前回データがないため、今回を基準として保存します（次回から比較します）。")
    else:
        changes = compare(old_prices, products)
        report(changes)

    save_snapshot(products, SNAPSHOT_FILE)


if __name__ == "__main__":
    main()
