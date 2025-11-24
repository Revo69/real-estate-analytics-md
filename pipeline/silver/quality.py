def calculate_quality_score(row: dict) -> float:
    important_fields = [
        row.get("price_mdl"),
        row.get("price_eur"),
        row.get("number_of_rooms"),
        row.get("total_area_m2"),
        row.get("floor"),
        row.get("total_floors"),
        row.get("region"),
        row.get("bathroom_count"),
    ]
    filled = sum(1 for v in important_fields if v not in (None, "", 0))
    return round(filled / len(important_fields), 3)

def assign_status(score: float) -> str:
    if score >= 0.85:
        return "success"
    elif score >= 0.55:
        return "partial"
    return "failed"
