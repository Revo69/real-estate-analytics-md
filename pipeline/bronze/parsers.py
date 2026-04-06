import re
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from .mappings import MAIN_FEATURES_MAP, ADDITIONAL_FEATURES_MAP
from typing import Dict, Optional
from utils.rates import get_current_rates, convert_currency
import logging

def extract_attr(soup, selector, attr_name, key_name):
    tag = soup.select_one(selector)
    if not tag:
        return {key_name: None}
    return {key_name: tag.get(attr_name)}


def extract_text(soup, selector, key_name, remove_prefix=None):
    tag = soup.select_one(selector)
    if not tag:
        return {key_name: None}
    text = tag.get_text(strip=True)
    if remove_prefix and text.startswith(remove_prefix):
        text = text[len(remove_prefix):].strip()
    return {key_name: text or None}


def extract_info_item(soup, label: str, key_name: str) -> dict:
    """
    Найти <p class="styles_advert__info__item___cXvq"> по началу текста,
    вернуть текст вложенного <span>.
    Пример: <p>Опубликовано:<span>3 апр. 2026, 16:33</span></p>
    """
    for p in soup.select("p.styles_advert__info__item___cXvq"):
        if p.get_text(strip=True).startswith(label):
            span = p.select_one("span.styles_advert__info__item__value__y3xkE")
            return {key_name: span.get_text(strip=True) if span else None}
    return {key_name: None}


def extract_list_features(soup, block_testid, key_selector, value_selectors, key_map, block_name):
    """
    Парсинг блока характеристик (ключ→значение).
    Ищет блок по data-testid, обходит все <li> в обеих колонках.
    """
    result = {block_name: {}}
    unknown_keys = []

    block = soup.find("div", attrs={"data-testid": block_testid})
    if not block:
        result[f"{block_name}_status"] = "block not found"
        return result

    for li in block.select("li"):
        key_tag = li.select_one(key_selector)
        if not key_tag:
            continue

        value_tag = None
        for vs in value_selectors:
            value_tag = li.select_one(vs)
            if value_tag:
                break

        if not value_tag:
            continue

        raw_key = key_tag.get_text(strip=True)
        raw_value = value_tag.get_text(strip=True)

        clean_key = key_map.get(raw_key)
        if clean_key:
            result[block_name][clean_key] = raw_value
        else:
            unknown_keys.append(raw_key)

    if unknown_keys:
        result[f"unknown_{block_name}"] = unknown_keys

    return result


def extract_boolean_features(soup, block_testid, item_selector, key_map, block_name):
    """
    Парсинг блока дополнительных характеристик (наличие = True).
    Ищет блок по data-testid, факт присутствия <li> = признак активен.
    """
    result = {block_name: {}}
    unknown_keys = []

    block = soup.find("div", attrs={"data-testid": block_testid})
    if not block:
        result[f"{block_name}_status"] = "block not found"
        return result

    for li in block.select(item_selector):
        key_tag = li.select_one(".styles_group__key__SXHV5")
        if not key_tag:
            continue
        raw_key = key_tag.get_text(strip=True)
        mapped_key = key_map.get(raw_key)
        if mapped_key:
            result[block_name][mapped_key] = True
        else:
            unknown_keys.append(raw_key)

    if unknown_keys:
        result[f"unknown_{block_name}"] = unknown_keys

    return result


def clean_number(num_str: str) -> Optional[int]:
    if not num_str:
        return None
    try:
        return int(num_str.replace(" ", "").replace("\u00A0", ""))
    except (ValueError, AttributeError):
        return None


def get_converted_prices(main_price: int, main_currency: str) -> Dict[str, Optional[int]]:
    result = {"mdl": None, "eur": None, "usd": None}
    if not main_price or not main_currency:
        return result
    main_currency = main_currency.lower()
    result[main_currency] = main_price
    for currency in ["mdl", "eur", "usd"]:
        if currency != main_currency:
            result[currency] = convert_currency(main_price, main_currency, currency)
    return result


def extract_all_prices(soup: BeautifulSoup) -> Dict[str, Optional[int]]:
    result = {"mdl": None, "eur": None, "usd": None}

    price_container = soup.find("div", class_=re.compile(r"styles_footer__"))
    if not price_container:
        return result

    full_text = price_container.get_text(separator=" ", strip=True)

    found_any = False

    if m := re.search(r"([\d\s\u00A0]+)\s*€", full_text):
        result["eur"] = clean_number(m.group(1))
        found_any = True

    if m := re.search(r"([\d\s\u00A0]+)\s*\$", full_text):
        result["usd"] = clean_number(m.group(1))
        found_any = True

    if m := re.search(r"([\d\s\u00A0]+)\s*MDL", full_text):
        result["mdl"] = clean_number(m.group(1))
        found_any = True

    if found_any:
        main_currency, main_price = None, None
        if result["eur"]:
            main_currency, main_price = "eur", result["eur"]
        elif result["usd"]:
            main_currency, main_price = "usd", result["usd"]
        elif result["mdl"]:
            main_currency, main_price = "mdl", result["mdl"]

        if main_currency and main_price:
            converted = get_converted_prices(main_price, main_currency)
            for currency in ["mdl", "eur", "usd"]:
                if result[currency] is None:
                    result[currency] = converted[currency]

    return result


def parse_features(url: str, driver=None) -> dict:
    try:
        driver.get(url)

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div.styles_advert__info__container__XKBza")
                )
            )
        except Exception:
            pass

        soup = BeautifulSoup(driver.page_source, "html.parser")
        features = {"url": url, "status": "success"}

        # --- Мета ---
        features.update(extract_attr(
            soup, 'meta[property="product:retailer_item_id"]', "content", "ad_id"
        ))

        # --- Инфо-блок: дата, просмотры, тип сделки ---
        features.update(extract_info_item(soup, "Опубликовано:", "publication_date"))
        features.update(extract_info_item(soup, "Тип предложения:", "deal_type"))

        items = soup.select("p.styles_advert__info__item___cXvq")
        logging.info(f"info items found: {len(items)}")
        for p in items:
            logging.info(f"  → {p.get_text(strip=True)}")

        # --- Пользователь ---
        features.update(extract_text(soup, "a.styles_user__card__login___Ug2V", "user_login"))

        # --- Адрес ---
        features.update(extract_text(soup, "div.styles_map__title__UgISm", "region"))

        # --- Описание ---
        features.update(extract_text(soup, "div.styles_description__body__qh1qw", "description"))

        # --- Характеристики (ключ → значение) ---
        features.update(extract_list_features(
            soup,
            block_testid="Характеристики",
            key_selector=".styles_group__key__SXHV5",
            value_selectors=[".styles_group__value__BlYqu", ".styles_group__link__GA7Xf"],
            key_map=MAIN_FEATURES_MAP,
            block_name="main_features"
        ))

        # --- Дополнительно (boolean) ---
        features.update(extract_boolean_features(
            soup,
            block_testid="Дополнительно",
            item_selector="li.styles_group__feature__GsOUi",
            key_map=ADDITIONAL_FEATURES_MAP,
            block_name="additional_features"
        ))

        # --- Цены ---
        features["price_json"] = extract_all_prices(soup)

        return features

    except Exception as e:
        return {"url": url, "status": f"error: {e}"}