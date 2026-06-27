"""상점 카탈로그(서버 권위). 키/슬롯은 static/js/dog/accessories.js와 일치해야 한다.

가격은 서버가 권위를 가진다(구매 검증). 표시명/슬롯도 여기서 내려준다.
"""

SHOP_ITEMS = {
    "bandana":    {"name": "반다나",       "slot": "body", "cost": 25},
    "party_hat":  {"name": "고깔모자",     "slot": "head", "cost": 30},
    "bowtie":     {"name": "나비넥타이",   "slot": "body", "cost": 35},
    "cap":        {"name": "야구모자",     "slot": "head", "cost": 40},
    "scarf":      {"name": "목도리",       "slot": "body", "cost": 45},
    "glasses":    {"name": "동그란 안경",  "slot": "face", "cost": 50},
    "sunglasses": {"name": "선글라스",     "slot": "face", "cost": 60},
    "cape":       {"name": "망토",         "slot": "body", "cost": 90},
    "crown":      {"name": "왕관",         "slot": "head", "cost": 120},
}
