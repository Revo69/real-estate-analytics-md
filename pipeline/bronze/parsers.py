import re
import logging

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from .mappings import MAIN_FEATURES_MAP, ADDITIONAL_FEATURES_MAP
from typing import Dict, Optional
from utils.rates import convert_currency
import random
import time


# ──────────────────────────────────────────────
# Helper extractors
# ──────────────────────────────────────────────


def extract_attr(soup, selector, attr_name, key_name):
    tag = soup.select_one(selector)
    if not tag:
        return {key_name: None}
    return {key_name: tag.get(attr_name)}


def extract_text(
    soup, selector, key_name, mapping=None, normalize=True, remove_prefix=None
):
    tag = soup.select_one(selector)
    if not tag:
        return {key_name: None}
    text = tag.get_text(strip=True)
    if remove_prefix and text.startswith(remove_prefix):
        text = text[len(remove_prefix) :]
    if normalize:
        text = text.strip() or None
    if mapping and text in mapping:
        text = mapping[text]
    return {key_name: text}


def extract_info_item(soup, label: str, key_name: str) -> dict:
    """
    Find <p class="styles_advert__info__item___cXvq"> that starts with label,
    return text of inner <span class="styles_advert__info__item__value__y3xkE">.

    Example HTML:
      <p class="styles_advert__info__item___cXvq">
        Тип предложения:
        <span class="styles_advert__info__item__value__y3xkE">Продам</span>
      </p>
    """
    for p in soup.select("p.styles_advert__info__item___cXvq"):
        if p.get_text(strip=True).startswith(label):
            span = p.select_one("span.styles_advert__info__item__value__y3xkE")
            return {key_name: span.get_text(strip=True) if span else None}
    return {key_name: None}


def extract_list_features(
    soup, block_testid, key_selector, value_selectors, key_map, block_name
):
    """
    Parse key-value list inside a div[data-testid=<block_testid>].

    value_selectors: list of CSS selectors tried in order — first match wins.
    Example:
      [".styles_group__value__BlYqu", ".styles_group__link__GA7Xf"]
    """
    result = {block_name: {}}
    unknown_keys = []

    block = soup.find("div", attrs={"data-testid": block_testid})
    if not block:
        result[f"{block_name}_status"] = "block_not_found"
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
    Parse boolean feature list (presence = True) inside a div[data-testid=<block_testid>].
    """
    result = {block_name: {}}
    unknown_keys = []

    block = soup.find("div", attrs={"data-testid": block_testid})
    if not block:
        result[f"{block_name}_status"] = "block_not_found"
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


# ──────────────────────────────────────────────
# Price extraction
# ──────────────────────────────────────────────


def clean_number(num_str: str) -> Optional[int]:
    if not num_str:
        return None
    try:
        return int(num_str.replace(" ", "").replace("\u00a0", ""))
    except (ValueError, AttributeError):
        return None


def get_converted_prices(
    main_price: int, main_currency: str
) -> Dict[str, Optional[int]]:
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
    """
    New design price selector: span.styles_price__main__kz3DX
    Example: '49 950 €'
    Falls back to regex scan of the wider price block.
    """
    result = {"mdl": None, "eur": None, "usd": None}
    found_any = False

    # Primary: dedicated price span
    price_tag = soup.select_one("span.styles_price__main__kz3DX")
    price_text = price_tag.get_text(strip=True) if price_tag else ""

    # Fallback: scan entire onboarding wrapper that contains currency rates
    if not price_text:
        wrapper = soup.select_one("div[data-onboarding='advert-currency-rates']")
        price_text = wrapper.get_text(separator=" ", strip=True) if wrapper else ""

    if price_text:
        if m := re.search(r"([\d\s\u00a0]+)\s*€", price_text):
            result["eur"] = clean_number(m.group(1))
            found_any = True
        if m := re.search(r"([\d\s\u00a0]+)\s*\$", price_text):
            result["usd"] = clean_number(m.group(1))
            found_any = True
        if m := re.search(r"([\d\s\u00a0]+)\s*MDL", price_text):
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


# ──────────────────────────────────────────────
# Main parser
# ──────────────────────────────────────────────

# Selectors that confirm the new-design page has loaded
_READINESS_SELECTORS = [
    "p.styles_advert__info__item___cXvq",  # info block (updated/views/deal type)
    "span.styles_price__main__kz3DX",  # price
    "div[data-testid='Характеристики']",  # features block
]


def parse_features(url: str, driver=None) -> dict:
    try:
        driver.get(url)

        # Wait for any of the readiness selectors
        page_ready = False
        for selector in _READINESS_SELECTORS:
            try:
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                logging.info(f"   ✅ Page ready, found: {selector}")
                page_ready = True
                break
            except Exception:
                continue

        if not page_ready:
            try:
                logging.warning(
                    f"   ⚠️ No readiness selector found. "
                    f"Title: '{driver.title}', URL: {driver.current_url}"
                )
                logging.warning(f"   📋 HTML preview:\n{driver.page_source[:3000]}")
            except Exception:
                pass
            return {"url": url, "status": "failed"}

        time.sleep(random.uniform(0.5, 1.0))  # let dynamic content settle

        soup = BeautifulSoup(driver.page_source, "html.parser")
        features = {"url": url, "status": "success"}

        # ── Meta ──────────────────────────────────────────────────────────
        features.update(
            extract_attr(
                soup, 'meta[property="product:retailer_item_id"]', "content", "ad_id"
            )
        )

        # ── Info block: updated date, deal type ───────────────────────────
        # "Обновлено:" or "Опубликовано:" depending on listing age
        pub = extract_info_item(soup, "Обновлено:", "publication_date")
        if not pub["publication_date"]:
            pub = extract_info_item(soup, "Опубликовано:", "publication_date")
        features.update(pub)

        features.update(extract_info_item(soup, "Тип предложения:", "deal_type"))

        # ── User login ────────────────────────────────────────────────────
        features.update(
            extract_text(soup, "a.styles_user__card__login___Ug2V", "user_login")
        )

        # ── Region / address ──────────────────────────────────────────────
        # New design: "Бельцы мун., Бельцы, Центр, str. Sennaia, 2"
        features.update(extract_text(soup, "div.styles_map__title__UgISm", "region"))

        # ── Description ───────────────────────────────────────────────────
        features.update(
            extract_text(soup, "div.styles_description__body__qh1qw", "description")
        )

        # ── Main features (Характеристики) ────────────────────────────────
        features.update(
            extract_list_features(
                soup,
                block_testid="Характеристики",
                key_selector=".styles_group__key__SXHV5",
                value_selectors=[
                    ".styles_group__value__BlYqu",  # plain text value
                    ".styles_group__link__GA7Xf",  # clickable link value
                ],
                key_map=MAIN_FEATURES_MAP,
                block_name="main_features",
            )
        )

        # ── Additional features (Дополнительно) ──────────────────────────
        features.update(
            extract_boolean_features(
                soup,
                block_testid="Дополнительно",
                item_selector="li.styles_group__feature__GsOUi",
                key_map=ADDITIONAL_FEATURES_MAP,
                block_name="additional_features",
            )
        )

        # ── Prices ────────────────────────────────────────────────────────
        features["price_json"] = extract_all_prices(soup)

        return features

    except Exception as e:
        import traceback

        logging.error(
            f"   ❌ parse_features error for {url}: {e}\n{traceback.format_exc()}"
        )
        return {"url": url, "status": f"error: {e}"}
