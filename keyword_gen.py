from itertools import product
import random
import pandas as pd

base_keywords = [
    "dişçi", "diş hekimi", "diş doktoru", "özel dişçi", "özel diş hekimi", "özel diş doktoru",
    "implant", "kanal", "dolgu", "lamina", "estetik diş", "acil dişçi", "yakın dişçi", "yakın diş hekimi",
    "diş kliniği", "diş polikliniği"
]

locations = [
    "şişli", "sisli", "beşiktaş", "besiktas", "levent", "mecidiyeköy", "mecidiyekoy", "nişantaşı", "nisantasi",
    "kağıthane", "kagithane", "perpa", "zeytinburnu", "fatih", "beyoğlu", "beyoglu", "sarıyer", "sariyer", "maslak", "istanbul"
]

suffixes = ["fiyat", "fiyatı", "yorum", "tavsiye", "öneri", "randevu", "acil", "en iyi", "nerede"]
prefixes = ["yakın", "bana yakın", "en yakın", "hemen"]

# Bazı suffix'lerin sadece şu base kelimelerle kullanılmasına izin ver
allowed_suffix_map = {
    "implant": ["fiyat", "fiyatı", "randevu", "tavsiye", "yorum"],
    "kanal": ["fiyat", "fiyatı", "randevu", "tavsiye"],
    "dolgu": ["fiyat", "fiyatı", "randevu"],
    "lamina": ["fiyat", "fiyatı", "randevu", "yorum"],
    "estetik diş": ["fiyat", "randevu", "yorum"],
    "dişçi": suffixes,
    "diş hekimi": suffixes,
    "diş doktoru": suffixes,
    "özel dişçi": suffixes,
    "özel diş hekimi": suffixes,
    "özel diş doktoru": suffixes,
    "diş kliniği": suffixes,
    "diş polikliniği": suffixes,
    "yakın dişçi": [],
    "yakın diş hekimi": [],
    "acil dişçi": [],
}

keyword_set = set()

def has_duplicate_location(phrase):
    count = sum(phrase.count(loc) for loc in locations)
    return count > 1

# Simple base+location
for base, loc in product(base_keywords, locations):
    if not has_duplicate_location(f"{loc} {base}"):
        keyword_set.add(f"[{loc} {base}]")
    if not has_duplicate_location(f"{base} {loc}"):
        keyword_set.add(f"[{base} {loc}]")

# Add suffix variations (mantıklı olanlarla sınırlı)
for base, loc, suf in product(base_keywords, locations, suffixes):
    if suf in allowed_suffix_map.get(base, []):
        for phrase in [f"{loc} {base} {suf}", f"{base} {suf} {loc}", f"{suf} {loc} {base}"]:
            if not has_duplicate_location(phrase):
                keyword_set.add(f"[{phrase}]")

# Add prefix variations (uzunluk sınırı + mantıklı kontrol)
for pre, base, loc in product(prefixes, base_keywords, locations):
    phrase1 = f"{pre} {base} {loc}"
    phrase2 = f"{pre} {loc} {base}"
    if not has_duplicate_location(phrase1):
        keyword_set.add(f"[{phrase1}]")
    if not has_duplicate_location(phrase2):
        keyword_set.add(f"[{phrase2}]")

# Complex combined variations (ama uzunluk 5 kelimeyi geçmesin)
for pre, base, loc, suf in product(prefixes, base_keywords, locations, suffixes):
    if suf in allowed_suffix_map.get(base, []):
        phrase1 = f"{pre} {base} {loc} {suf}"
        phrase2 = f"{pre} {loc} {base} {suf}"
        if len(phrase1.split()) <= 5 and not has_duplicate_location(phrase1):
            keyword_set.add(f"[{phrase1}]")
        if len(phrase2.split()) <= 5 and not has_duplicate_location(phrase2):
            keyword_set.add(f"[{phrase2}]")

# Shuffle and limit
keyword_list = list(keyword_set)
random.shuffle(keyword_list)
keyword_list = keyword_list[:50000]

df = pd.DataFrame(keyword_list, columns=["keyword"])
df.to_csv("exact_match_keywords_50k_filtered.csv", index=False)
