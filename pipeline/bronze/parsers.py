import re
import requests
from bs4 import BeautifulSoup
from .mappings import MAIN_FEATURES_MAP, ADDITIONAL_FEATURES_MAP
from typing import Dict, Optional


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

def extract_list_features(soup, block_selector, key_selector, value_selector, key_map, block_name):
    result = {block_name: {}}
    unknown_keys = []

    block = soup.select_one(block_selector)
    if block:
        for li in block.select("li"):
            key_tag = li.select_one(key_selector)
            value_tag = li.select_one(value_selector)
            if not key_tag or not value_tag:
                continue

            raw_key = key_tag.get_text(strip=True)
            raw_value = value_tag.get_text(strip=True)

            clean_key = key_map.get(raw_key)
            if clean_key:
                result[block_name][clean_key] = raw_value
            else:
                unknown_keys.append(raw_key)
    else:
        result[f"{block_name}_status"] = "Нет блока характеристик"

    if unknown_keys:
        result[f"unknown_{block_name}"] = unknown_keys

    return result


def extract_boolean_features(soup, block_selector, item_selector, key_map, block_name):
    result = {block_name: {}}
    unknown_keys = []

    block = soup.select_one(block_selector)
    if block:
        for item in block.select(item_selector):
            raw_key = item.get_text(strip=True)
            mapped_key = key_map.get(raw_key)
            if mapped_key:
                result[block_name][mapped_key] = True
            else:
                unknown_keys.append(raw_key)
    else:
        result[f"{block_name}_status"] = "Нет блока характеристик"

    if unknown_keys:
        result[f"unknown_{block_name}"] = unknown_keys

    return result

def extract_attr(soup, selector, attr_name, key_name):
    tag = soup.select_one(selector)
    if not tag:
        return {key_name: None}
    return {key_name: tag.get(attr_name)}

def extract_text(soup, selector, key_name, mapping=None, normalize=True, remove_prefix=None):
    tag = soup.select_one(selector)
    if not tag:
        return {key_name: None}

    text = tag.get_text(strip=True)

    if remove_prefix and text.startswith(remove_prefix):
        text = text[len(remove_prefix):]

    if normalize:
        text = text.strip() or None

    if mapping and text in mapping:
        text = mapping[text]

    return {key_name: text}

def clean_number(num_str: str) -> int:
    """Очистить строку числа от пробелов и неразрывных пробелов."""
    return int(num_str.replace(" ", "").replace("\u00A0", ""))

def extract_all_prices(soup: BeautifulSoup) -> Dict[str, Optional[int]]:
    result = {"mdl": None, "eur": None, "usd": None}

    # --- 1. Основная цена ---
    main_span = soup.find("span", class_="styles_footer__main__8seZ7")
    if main_span:
        text = main_span.get_text(" ", strip=True)

        if "€" in text:
            m = re.search(r"([\d\s\u00A0]+)", text)
            if m:
                result["eur"] = clean_number(m.group(1))
        elif "$" in text:
            m = re.search(r"([\d\s\u00A0]+)", text)
            if m:
                result["usd"] = clean_number(m.group(1))
        elif "MDL" in text:
            m = re.search(r"([\d\s\u00A0]+)", text)
            if m:
                result["mdl"] = clean_number(m.group(1))

    # --- 2. Конвертированные цены ---
    for li in soup.select("ul.styles_footer__converted__kKoJd li"):
        text = li.get_text(" ", strip=True)

        m_eur = re.search(r"([\d\s\u00A0]+)\s*€", text)
        if m_eur:
            result["eur"] = clean_number(m_eur.group(1))

        m_usd = re.search(r"([\d\s\u00A0]+)\s*\$", text)
        if m_usd:
            result["usd"] = clean_number(m_usd.group(1))

        m_mdl = re.search(r"([\d\s\u00A0]+)\s*MDL", text)
        if m_mdl:
            result["mdl"] = clean_number(m_mdl.group(1))
    return result


def parse_features(url: str) -> dict:
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        features = {"url": url, "status": "success"}

        features.update(extract_attr(soup, 'meta[property="product:retailer_item_id"]', "content", "ad_id"))
        features.update(extract_text(soup, "p.styles_date__voWnk", "publication_date", remove_prefix="Дата публикации:"))
        features.update(extract_text(soup, "a.styles_owner__login__VKE71", "user_login"))
        features.update(extract_text(soup, "p.styles_type___J9Dy", "deal_type", remove_prefix="Тип:"))
        features.update(extract_text(soup, "div.styles_region__7lsaj", "region", remove_prefix="Регион:"))
        features.update(extract_text(soup, "div.styles_description__8_RRa div.styles_textcontent__XH6FS.styles_desktop__d_kP8", "description"))

        features.update(extract_list_features(
            soup,
            "div.styles_features__left__ON_QP",
            "span.styles_group__key__uRhnQ",
            "span.styles_group__value__XN7OI",
            MAIN_FEATURES_MAP,
            "main_features"
        ))

        features.update(extract_boolean_features(
            soup,
            "div.styles_features__right__Sn6fV",
            "span.styles_group__key__uRhnQ",
            ADDITIONAL_FEATURES_MAP,
            "additional_features"
        ))

        # 💰 Цены в JSON
        features["price_json"] = extract_all_prices(soup)

        return features

    
    except Exception as e:
        return {"url": url, "status": f"error: {e}"}
