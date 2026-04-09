import re
import logging 
import requests
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from .mappings import MAIN_FEATURES_MAP, ADDITIONAL_FEATURES_MAP
from typing import Dict, Optional
from utils.rates import get_current_rates, convert_currency
from selenium.webdriver.common.action_chains import ActionChains
import random
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

def set_old_version_cookie(driver):
    try:
        driver.add_cookie({
            "name": "designVersion",
            "value": "v1",
            "domain": ".999.md",
            "path": "/"
        })
        logging.info("   🍪 Cookie designVersion=v1 set")
    except Exception as e:
        logging.debug(f"   Cookie set error: {e}")

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

def clean_number(num_str: str) -> Optional[int]:
    """Clean numeric string from spaces and non-breaking spaces."""
    if not num_str:
        return None
    try:
        return int(num_str.replace(" ", "").replace("\u00A0", ""))
    except (ValueError, AttributeError):
        return None

def get_converted_prices(main_price: int, main_currency: str) -> Dict[str, Optional[int]]:
    """Convert the main price to all currencies using current exchange rates."""
    result = {"mdl": None, "eur": None, "usd": None}
    
    if not main_price or not main_currency:
        return result
    
    main_currency = main_currency.lower()
    result[main_currency] = main_price
    
        # Convert to other currencies using current exchange rates
    for currency in ["mdl", "eur", "usd"]:
        if currency != main_currency:
            result[currency] = convert_currency(main_price, main_currency, currency)
    
    return result

def extract_all_prices(soup: BeautifulSoup) -> Dict[str, Optional[int]]:
    """
    Extract prices in all currencies.
    Strategy: parse what's in HTML; convert the rest using current exchange rates.
    """
    result = {"mdl": None, "eur": None, "usd": None}
    
    price_container = soup.find("div", class_=re.compile(r"styles_footer__"))
    if not price_container:
        return result
    
    # Get full text from the price block
    full_text = price_container.get_text(separator=" ", strip=True)
        
        # Parse any found currencies
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
    
    # If at least one currency is found, recalculate the others
    if found_any:
        # Determine the main currency (not None)
        main_currency = None
        main_price = None
        
        if result["eur"]:
            main_currency = "eur"
            main_price = result["eur"]
        elif result["usd"]:
            main_currency = "usd"
            main_price = result["usd"]
        elif result["mdl"]:
            main_currency = "mdl"
            main_price = result["mdl"]
        
        # Convert missing currencies
        if main_currency and main_price:
            converted = get_converted_prices(main_price, main_currency)
            for currency in ["mdl", "eur", "usd"]:
                if result[currency] is None:
                    result[currency] = converted[currency]
                    
    return result


def parse_features(url: str, driver=None) -> dict:
    try:
        current_url = driver.current_url
        if "999.md" not in current_url:
            driver.get("https://999.md/ru")
            time.sleep(1)
        
        driver.get(url)

        set_old_version_cookie(driver)
        
        # Перезагружаем страницу с новым куки
        driver.get(url)
        
        time.sleep(random.uniform(2.0, 3.0))
        
        if "rd-visa-logo" in driver.page_source:
            logging.warning(f"   ⚠️ Still new version after cookie set: {url}")

        page_ready = False
        for selector in [
            "div.styles_features__left__ON_QP",  # блок характеристик
            "div.styles_footer__sKQxZ",           # блок с ценой и регионом  
            "a.styles_owner__login__VKE71",        # логин владельца
        ]:
            try:
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                logging.info(f"   ✅ Page ready, found: {selector}")
                page_ready = True
                break
            except:
                continue
        
        if not page_ready:
            try:
                html_preview = driver.page_source[:5000]
                logging.warning(f"   📄 Title: '{driver.title}', URL: {driver.current_url}")
                logging.warning(f"   📋 HTML preview:\n{html_preview}")
            except Exception as dump_err:
                logging.warning(f"   ⚠️ Could not dump: {dump_err}")
            
            return {"url": url, "status": "failed"}
        
        soup = BeautifulSoup(driver.page_source, "html.parser")

        features = {"url": url, "status": "success"}

        features.update(extract_attr(soup, 'meta[property="product:retailer_item_id"]', "content", "ad_id"))
        #features.update(extract_text(soup, "p.styles_date__voWnk", "publication_date", remove_prefix="Дата публикации:"))
        date_tag = soup.select_one("p.styles_date__voWnk")
        if date_tag:
            date_text = date_tag.get_text(strip=True)
            for prefix in ["Дата публикации:", "Дата обновления:"]:
                if date_text.startswith(prefix):
                    date_text = date_text[len(prefix):].strip()
                    break
            features["publication_date"] = date_text
        else:
            features["publication_date"] = None
        
        features.update(extract_text(soup, "a.styles_owner__login__VKE71", "user_login"))
        features.update(extract_text(soup, "p.styles_type___J9Dy", "deal_type", remove_prefix="Тип:"))
        features.update(extract_text(soup, "div.styles_region__7lsaj", "region", remove_prefix="Регион:"))
        features.update(extract_text(soup, "div.styles_description__8_RRa div.styles_textcontent__XH6FS.styles_desktop__d_kP8", "description"))

        features.update(extract_list_features(
            soup,
            "div.styles_features__left__ON_QP",
            ".styles_group__key__uRhnQ",
            ".styles_group__value__XN7OI",
            MAIN_FEATURES_MAP,
            "main_features"
        ))

        features.update(extract_boolean_features(
            soup,
            "div.styles_features__right__Sn6fV",
            ".styles_group__key__uRhnQ",
            ADDITIONAL_FEATURES_MAP,
            "additional_features"
        ))

        # 💰 Prices in JSON (now with all currencies)
        features["price_json"] = extract_all_prices(soup)

        return features

    except Exception as e:
        return {"url": url, "status": f"error: {e}"}

