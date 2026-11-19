"""Ko'p tilli (uz/ru/en) qidiruv: markaz nomi, kurs, yo'nalish bo'yicha.

Qanday ishlaydi:
1. Matn normallashtiriladi: kichik harf, apostroflar olib tashlanadi, kirill -> lotin.
2. "Podgotovka k SAT" kabi so'rovlardan keraksiz so'zlar (stop-so'zlar) tashlanadi.
3. Har bir so'rov so'zi markaz so'zlaridan biriga mos kelishi kerak:
   to'liq, boshi (prefiks), ichida (3+ harf) yoki xatoli yozuv (difflib >= 0.8).
4. Indeks xotirada saqlanadi, Center/Course/Subject o'zgarganda tozalanadi.
"""
import re
import unicodedata
from difflib import SequenceMatcher

from django.core.cache import cache
from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

CYR = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "ж": "j", "з": "z",
    "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
    "с": "s", "т": "t", "у": "u", "ф": "f", "х": "x", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sh",
    "ъ": "", "ы": "i", "ь": "", "э": "e", "ю": "yu", "я": "ya", "ў": "o", "қ": "q", "ғ": "g", "ҳ": "h",
}
STOPWORDS = {
    "k", "v", "na", "dlya", "po", "i", "va", "uchun", "bilan", "the", "for", "to", "of", "and",
    "podgotovka", "preparation", "prep", "kurs", "kursi", "kurslari", "course", "courses", "kursy",
    "markaz", "markazi", "center", "centre", "tsentr", "oquv", "uquv", "uchebnyy", "uchebniy",
    "tayyorlov", "tayyorlash", "kursiga", "darslari", "dars", "lessons", "school", "maktab", "tili",
    "yazik", "yazyk", "language",
}
# Bir ma'noli so'zlar guruhlari (normallashtirilgan, lotin): har biri bir-biriga teng.
SYNONYM_GROUPS = [
    {"ingliz", "english", "angliyskiy", "angliyskiy", "inglizcha", "angliyski"},
    {"rus", "russian", "russkiy", "ruscha"},
    {"matematika", "math", "maths", "mathematics", "matem"},
    {"dasturlash", "programming", "programmirovanie", "programmalash", "coding", "kodlash"},
    {"fizika", "physics", "fizik"},
    {"kimyo", "chemistry", "ximiya", "ximiyo"},
    {"biologiya", "biology"},
    {"nemis", "german", "nemetskiy"},
    {"koreys", "korean", "koreyskiy"},
    {"xitoy", "chinese", "kitayskiy"},
    {"arab", "arabic", "arabskiy"},
]
_SYN = {}
for _g in SYNONYM_GROUPS:
    for _w in _g:
        _SYN[_w] = _g

_APOS = re.compile(r"[ʻʼ'`’‘´]")
_NON = re.compile(r"[^0-9a-z]+")


def normalize(text):
    text = unicodedata.normalize("NFKC", text or "").lower()
    text = _APOS.sub("", text)
    text = "".join(CYR.get(ch, ch) for ch in text)
    return _NON.sub(" ", text).strip()


def tokens(text, drop_stop=False):
    result = normalize(text).split()
    if drop_stop:
        result = [t for t in result if t not in STOPWORDS]
    return result


def _token_matches(q, word):
    if q == word or word.startswith(q):
        return True
    if len(q) >= 3 and q in word:
        return True
    if q in _SYN and word in _SYN[q]:
        return True
    if len(q) >= 4 and len(word) >= 4 and abs(len(q) - len(word)) <= 2:
        return SequenceMatcher(None, q, word).ratio() >= 0.8
    return False


CACHE_KEY = "centers_search_index_v1"


def _build_index():
    from .models import Center

    index = {}
    qs = Center.objects.prefetch_related("subjects", "courses")
    for c in qs:
        parts = [c.name, c.alternative_names]
        for s in c.subjects.all():
            parts += [s.name, s.alternative_names]
        for course in c.courses.all():
            parts += [course.name, course.alternative_names]
        words = set()
        for p in parts:
            # vergul bilan yozilgan muqobil nomlar ham alohida so'zlarga bo'linadi
            words.update(tokens(p))
        index[c.pk] = words
    return index


def get_index():
    index = cache.get(CACHE_KEY)
    if index is None:
        index = _build_index()
        cache.set(CACHE_KEY, index, 3600)
    return index


def search_center_ids(query):
    """Qidiruvga mos markaz id'lari to'plami. Bo'sh so'rov -> None (filtr yo'q)."""
    q_tokens = tokens(query, drop_stop=True) or tokens(query)
    if not q_tokens:
        return None
    matched = set()
    for pk, words in get_index().items():
        if all(any(_token_matches(q, w) for w in words) for q in q_tokens):
            matched.add(pk)
    return matched


def text_matches(query, *texts):
    """Bitta yozuv (kurs/yo'nalish nomi) so'rovga mosmi."""
    q_tokens = tokens(query, drop_stop=True) or tokens(query)
    if not q_tokens:
        return False
    words = set()
    for t in texts:
        words.update(tokens(t))
    return all(any(_token_matches(q, w) for w in words) for q in q_tokens)


def invalidate(*args, **kwargs):
    cache.delete(CACHE_KEY)


def connect_signals():
    from .models import Center, Course, Subject

    for model in (Center, Course, Subject):
        post_save.connect(invalidate, sender=model, weak=False, dispatch_uid=f"search_{model.__name__}_s")
        post_delete.connect(invalidate, sender=model, weak=False, dispatch_uid=f"search_{model.__name__}_d")
    m2m_changed.connect(invalidate, sender=Center.subjects.through, weak=False, dispatch_uid="search_cs")
    m2m_changed.connect(invalidate, sender=Course.centers.through, weak=False, dispatch_uid="search_cc")
