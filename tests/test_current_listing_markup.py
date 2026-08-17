from bs4 import BeautifulSoup

from pipeline.bronze.mappings import ADDITIONAL_FEATURES_MAP, MAIN_FEATURES_MAP
from pipeline.bronze.parsers import (
    extract_all_prices,
    extract_boolean_features,
    extract_info_item,
    extract_list_features,
    extract_region,
    extract_text,
    parse_features,
)


CURRENT_LISTING_HTML = """
<html>
  <head>
    <meta property="product:retailer_item_id" content="105032701">
    <meta property="product:price:currency" content="EUR">
    <meta property="product:price:amount" content="123900">
  </head>
  <body>
    <div class="styles-module-scss-module__RKm0hG__advert__info__item">
      Обновлено:<span class="styles-module-scss-module__RKm0hG__advert__info__item__value">14 авг. 2026, 15:42</span>
    </div>
    <div class="styles-module-scss-module__RKm0hG__advert__info__item">
      Тип предложения:<span class="styles-module-scss-module__RKm0hG__advert__info__item__value">Продам</span>
    </div>
    <a class="styles-module-scss-module__isYV2a__user__card__login">Proimobil</a>
    <div data-block="description"><div itemprop="description">Описание квартиры</div></div>
    <div data-testid="Характеристики">
      <li class="styles-module-scss-module__cE7kPa__group__feature">
        <span class="styles-module-scss-module__cE7kPa__group__key">Количество комнат</span>
        <a class="styles-module-scss-module__cE7kPa__group__link">2-х комнатная квартира</a>
      </li>
      <li class="styles-module-scss-module__cE7kPa__group__feature">
        <span class="styles-module-scss-module__cE7kPa__group__key">Общая площадь</span>
        <span class="styles-module-scss-module__cE7kPa__group__value">58 м²</span>
      </li>
    </div>
    <div data-testid="Дополнительно">
      <li class="styles-module-scss-module__cE7kPa__group__feature">
        <span class="styles-module-scss-module__cE7kPa__group__key">Лифт</span>
      </li>
    </div>
    <div data-block="map">
      <div class="styles-module-scss-module__No-yhq__map__title">Кишинёв мун., Кишинёв, Ботаника</div>
    </div>
  </body>
</html>
"""


class StaticListingDriver:
    title = "Current 999.md listing"
    current_url = "https://999.md/ru/105032701"
    page_source = CURRENT_LISTING_HTML

    def get(self, url):
        self.current_url = url


class ImmediateWait:
    def __init__(self, *_):
        pass

    def until(self, _):
        return True


def test_current_listing_markup_extracts_core_listing_data(monkeypatch):
    monkeypatch.setattr("pipeline.bronze.parsers.convert_currency", lambda *_: 1)
    monkeypatch.setattr("pipeline.bronze.parsers.WebDriverWait", ImmediateWait)
    monkeypatch.setattr("pipeline.bronze.parsers.random.uniform", lambda *_: 0)
    monkeypatch.setattr("pipeline.bronze.parsers.time.sleep", lambda _: None)

    record = parse_features("https://999.md/ru/105032701", StaticListingDriver())

    assert record["status"] == "success"
    assert record["ad_id"] == "105032701"
    assert record["publication_date"] == "14 авг. 2026, 15:42"
    assert record["deal_type"] == "Продам"
    assert record["user_login"] == "Proimobil"
    assert record["region"] == "Кишинёв мун., Кишинёв, Ботаника"
    assert record["description"] == "Описание квартиры"
    assert record["main_features"] == {
        "number_of_rooms": "2-х комнатная квартира",
        "total_area_m2": "58 м²",
    }
    assert record["additional_features"] == {"elevator": True}
    assert record["price_json"]["eur"] == 123900


def test_current_listing_selectors_match_the_current_markup(monkeypatch):
    monkeypatch.setattr("pipeline.bronze.parsers.convert_currency", lambda *_: 1)
    soup = BeautifulSoup(CURRENT_LISTING_HTML, "html.parser")

    assert extract_info_item(soup, "Обновлено:", "publication_date") == {
        "publication_date": "14 авг. 2026, 15:42"
    }
    assert extract_info_item(soup, "Тип предложения:", "deal_type") == {
        "deal_type": "Продам"
    }
    assert extract_region(soup) == {"region": "Кишинёв мун., Кишинёв, Ботаника"}
    assert extract_text(
        soup, "[data-block='description'] [itemprop='description']", "description"
    ) == {"description": "Описание квартиры"}
    assert extract_list_features(
        soup,
        "Характеристики",
        "[class*='group__key']",
        ["[class*='group__value']", "[class*='group__link']"],
        MAIN_FEATURES_MAP,
        "main_features",
    )["main_features"] == {
        "number_of_rooms": "2-х комнатная квартира",
        "total_area_m2": "58 м²",
    }
    assert extract_boolean_features(
        soup,
        "Дополнительно",
        "li[class*='group__feature']",
        ADDITIONAL_FEATURES_MAP,
        "additional_features",
    )["additional_features"] == {"elevator": True}
    assert extract_all_prices(soup)["eur"] == 123900
