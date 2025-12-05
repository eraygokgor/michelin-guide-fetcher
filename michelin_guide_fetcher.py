import json
import os
import time

import pandas as pd
import requests
import urllib3
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

# SSL uyarılarını kapat (sadece geliştirme için)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class MichelinScraper:
    def __init__(self):
        self.api_url = "https://8nvhrd7onv-dsn.algolia.net/1/indexes/*/queries"
        self.app_id = os.getenv("ALGOLIA_APP_ID")
        self.api_key = os.getenv("ALGOLIA_API_KEY")
        self.headers = {
            "x-algolia-agent": "Algolia for JavaScript (4.19.1); Browser (lite)",
            "x-algolia-api-key": self.api_key,
            "x-algolia-application-id": self.app_id,
            "content-type": "application/json",
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
            "origin": "https://guide.michelin.com",
            "referer": "https://guide.michelin.com/",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "cross-site",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
        }

    def get_restaurants(self, page=0, hits_per_page=48):
        """Belirli bir sayfadaki restoranları çeker"""

        # Tarayıcıdaki gibi tam parametreler
        params = (
            f"aroundLatLngViaIP=true&"
            f"aroundRadius=all&"
            f"attributesToHighlight=%5B%5D&"
            f"attributesToRetrieve=%5B%22_geoloc%22%2C%22region%22%2C%22area_name%22%2C%22chef%22%2C%22city%22%2C%22country%22%2C%22cuisines%22%2C%22currency%22%2C%22good_menu%22%2C%22identifier%22%2C%22image%22%2C%22images%22%2C%22main_image%22%2C%22michelin_award%22%2C%22name%22%2C%22slug%22%2C%22new_table%22%2C%22offers%22%2C%22offers_size%22%2C%22online_booking%22%2C%22other_urls%22%2C%22region_code%22%2C%22site_slug%22%2C%22site_name%22%2C%22take_away%22%2C%22delivery%22%2C%22price_category%22%2C%22currency_symbol%22%2C%22url%22%2C%22green_star%22%2C%22michelin_guide_hotel%22%2C%22objectType%22%5D&"
            f"facets=%5B%22area_slug%22%2C%22booking_provider%22%2C%22categories.lvl0%22%2C%22city.slug%22%2C%22country.cname%22%2C%22country.slug%22%2C%22cuisines.slug%22%2C%22days_open%22%2C%22delivery%22%2C%22delivery_provider%22%2C%22distinction.slug%22%2C%22facilities.slug%22%2C%22good_menu%22%2C%22green_star.slug%22%2C%22meal_times%22%2C%22new_table%22%2C%22offers%22%2C%22online_booking%22%2C%22price_category.slug%22%2C%22region.slug%22%2C%22tag_thematic.slug%22%2C%22take_away%22%5D&"
            f"filters=status%3APublished&"
            f"hitsPerPage={hits_per_page}&"
            f"maxValuesPerFacet=200&"
            f"optionalFilters=%5B%22sites%3Atr%22%5D&"
            f"page={page}&"
            f"query=&"
            f"tagFilters="
        )

        payload = {"requests": [{"indexName": "prod-restaurants-tr", "params": params}]}

        try:
            response = requests.post(
                self.api_url, headers=self.headers, json=payload, verify=False
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Hata oluştu: {e}")
            if hasattr(e.response, "text"):
                print(f"Response: {e.response.text}")
            return None

    def extract_restaurant_data(self, hit):
        """Her restorandan gerekli bilgileri çıkarır"""

        return {
            "name": hit.get("name"),
            "city": hit.get("city", {}).get("name"),
            "region": hit.get("region", {}).get("name"),
            "country": hit.get("country", {}).get("name"),
            "michelin_award": hit.get("michelin_award"),
            "cuisines": ", ".join(
                [c.get("label", "") for c in hit.get("cuisines", [])]
            ),
            "price_category": hit.get("price_category", {}).get("label"),
            "price_symbol": hit.get("currency_symbol"),
            "online_booking": hit.get("online_booking"),
            "latitude": hit.get("_geoloc", {}).get("lat"),
            "longitude": hit.get("_geoloc", {}).get("lng"),
            "url": "https://guide.michelin.com" + (hit.get("url") or ""),
            "image_url": (
                hit.get("main_image", {}).get("url") if hit.get("main_image") else None
            ),
            "identifier": hit.get("identifier"),
            "slug": hit.get("slug"),
            "take_away": hit.get("take_away"),
            "delivery": hit.get("delivery"),
            "chef": hit.get("chef"),
        }

    def scrape_all_restaurants(self, max_pages=None):
        """Tüm restoranları çeker"""

        all_restaurants = []
        page = 0

        print("Veri çekme başlıyor...")

        # İlk sayfa ile toplam sayfa sayısını öğren
        first_response = self.get_restaurants(page=0)
        if not first_response:
            return []

        total_pages = first_response["results"][0]["nbPages"]
        total_hits = first_response["results"][0]["nbHits"]

        print(f"Toplam {total_hits} restoran, {total_pages} sayfada bulundu")

        # Eğer max_pages belirtilmişse onu kullan
        if max_pages:
            total_pages = min(total_pages, max_pages)

        # İlk sayfanın verilerini ekle
        for hit in first_response["results"][0]["hits"]:
            restaurant = self.extract_restaurant_data(hit)
            all_restaurants.append(restaurant)

        # Kalan sayfaları çek
        for page in range(1, total_pages):
            print(f"Sayfa {page + 1}/{total_pages} çekiliyor...")

            response = self.get_restaurants(page=page)

            if response and "results" in response:
                for hit in response["results"][0]["hits"]:
                    restaurant = self.extract_restaurant_data(hit)
                    all_restaurants.append(restaurant)

            # Rate limiting için bekleme
            time.sleep(0.5)

        print(f"\nToplam {len(all_restaurants)} restoran çekildi!")
        return all_restaurants

    def save_to_csv(self, restaurants, filename="michelin_restaurants.csv"):
        """Verileri CSV'ye kaydeder"""
        df = pd.DataFrame(restaurants)
        df.to_csv(filename, index=False, encoding="utf-8-sig")
        print(f"Veriler '{filename}' dosyasına kaydedildi!")
        return df


# Kullanım örneği
if __name__ == "__main__":
    scraper = MichelinScraper()

    # Sadece ilk 5 sayfayı test etmek için (silip None yapabilirsin)
    restaurants = scraper.scrape_all_restaurants(max_pages=None)

    # Verileri CSV'ye kaydet
    df = scraper.save_to_csv(restaurants)

    # DataFrame'in genel bilgilerini göster
    print("\nDataFrame Bilgileri:")
    print(df.info())
    print("\n" + "=" * 50)

    # İlk 5 restoranı göster
    print("\nİlk 5 restoran:")
    print(df.head())

    # Kolon isimlerini göster
    print("\n" + "=" * 50)
    print("Mevcut kolonlar:")
    print(df.columns.tolist())

    # Michelin yıldızlı restoranları göster (eğer varsa)
    if "michelin_award" in df.columns:
        print("\n" + "=" * 50)
        print("Michelin Ödül Türleri:")
        print(df["michelin_award"].value_counts())

        if (df["michelin_award"] == "ONE_STAR").any():
            print("\n1 Yıldızlı Restoranlar:")
            print(df[df["michelin_award"] == "ONE_STAR"][["name", "city", "cuisines"]])
    else:
        print("\n⚠️ 'michelin_award' kolonu bulunamadı!")

    # Özet istatistikler
    print("\n" + "=" * 50)
    print("Özet İstatistikler:")
    print(f"Toplam restoran sayısı: {len(df)}")
    if "city" in df.columns:
        print(f"Farklı şehir sayısı: {df['city'].nunique()}")
        print(f"\nEn çok restoran olan şehirler:")
        print(df["city"].value_counts().head(10))
