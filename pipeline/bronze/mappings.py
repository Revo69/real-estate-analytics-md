# Original site label → normalized key (snake_case, English, concise)

# Mapping dictionary for "Main characteristics" block (apartment details)
MAIN_FEATURES_MAP = {
    "Автор объявления": "listing_author",
    "Количество комнат": "number_of_rooms",
    "Ливинг": "living_room",              # если это отдельная комната-гостиная
    "Общая площадь": "total_area_m2",
    "Жилой фонд": "housing_type",         # вторичный / новострой
    "Этаж": "floor",
    "Количество этажей": "total_floors",
    "Застройщик": "developer",
    "Тип здания": "building_type",
    "Состояние квартиры": "apartment_condition",
    "Планировка": "layout",
    "Жилая площадь": "living_area_m2",
    "Площадь кухни": "kitchen_area_m2",
    "Санузел": "bathroom_count",           # количество
    "Балкон / лоджия": "balcony_loggia",
    "Высота потолков": "ceiling_height_cm",
    "Парковочное место": "parking_space",
}

# Mapping dictionary for "Additional characteristics" block (apartment details)
ADDITIONAL_FEATURES_MAP = {
    "Готова к въезду": "ready_to_move_in",
    "Пристройка": "extension",
    "Терраса": "terrace",
    "Отдельный вход": "separate_entrance",
    "Парковая зона": "park_area",
    "Меблированная": "furnished",
    "С бытовой техникой": "with_appliances",
    "Автономное отопление": "autonomous_heating",
    "Кондиционер": "air_conditioning",
    "Теплые полы": "underfloor_heating",
    "Стеклопакет": "double_glazing",
    "Панорамные окна": "panoramic_windows",
    "Паркет": "parquet_floor",
    "Ламинат": "laminate_floor",
    "Бронированная дверь": "security_door",
    "Телефонная линия": "telephone_line",
    "Система \"умный дом\"": "smart_home",
    "Домофон": "intercom",
    "Интернет": "internet",
    "ТВ кабель": "cable_tv",
    "Сигнализация": "alarm_system",
    "Видеонаблюдение": "video_surveillance",
    "Лифт": "elevator",
    "Детская площадка": "playground",
}
