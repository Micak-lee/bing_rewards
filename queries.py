"""Random search query generation from keyword banks."""
import random
from pathlib import Path

QUERIES_DIR = Path(__file__).parent / "queries"

_TEMPLATES_ZH = [
    "{kw}",
    "{kw} 最新",
    "{kw} 是什么",
    "{kw} 怎么学",
    "关于 {kw}",
    "{kw} 教程",
    "{kw} 排名",
    "{kw} 推荐",
    "如何 {kw}",
    "{kw} 攻略",
    "{kw} 是什么意思",
    "{kw} 入门",
]

_TEMPLATES_EN = [
    "{kw}",
    "{kw} news",
    "what is {kw}",
    "how to {kw}",
    "best {kw}",
    "{kw} tutorial",
    "{kw} guide",
    "{kw} review",
    "{kw} tips",
    "learn {kw}",
    "{kw} vs",
    "top {kw}",
]


class QueryGenerator:
    """Generates realistic search queries from keyword banks."""

    def __init__(self, zh_keywords: list[str] | None = None, en_keywords: list[str] | None = None):
        self.zh_keywords = zh_keywords or []
        self.en_keywords = en_keywords or []
        self._used: set[str] = set()

    @classmethod
    def from_files(
        cls,
        zh_path: Path | None = None,
        en_path: Path | None = None,
    ) -> "QueryGenerator":
        """Load keywords from text files (one keyword per line)."""
        zh_path = zh_path or QUERIES_DIR / "zh_keywords.txt"
        en_path = en_path or QUERIES_DIR / "en_keywords.txt"

        zh_keywords = []
        en_keywords = []

        if zh_path.exists():
            zh_keywords = [
                line.strip()
                for line in zh_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        if en_path.exists():
            en_keywords = [
                line.strip()
                for line in en_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        return cls(zh_keywords, en_keywords)

    def generate(self, language: str = "mix") -> str:
        """Generate a single search query.

        Args:
            language: "zh", "en", or "mix"

        Returns:
            A search query string. Guaranteed unique within this session.
        """
        if language == "zh":
            pool = self.zh_keywords
            templates = _TEMPLATES_ZH
        elif language == "en":
            pool = self.en_keywords
            templates = _TEMPLATES_EN
        else:
            # Mix: use both pools
            if random.random() < 0.5 and self.zh_keywords:
                pool = self.zh_keywords
                templates = _TEMPLATES_ZH
            else:
                pool = self.en_keywords
                templates = _TEMPLATES_EN

        if not pool:
            # Fallback if a pool is empty but the other has content
            if language == "mix" and self.zh_keywords:
                pool, templates = self.zh_keywords, _TEMPLATES_ZH
            elif language == "mix" and self.en_keywords:
                pool, templates = self.en_keywords, _TEMPLATES_EN
            else:
                return f"interesting things {random.randint(1000, 9999)}"

        # Try to generate a unique query
        for _ in range(100):
            kw = random.choice(pool)
            template = random.choice(templates)
            query = template.replace("{kw}", kw)
            if query not in self._used:
                self._used.add(query)
                return query

        # Fallback: add random suffix to avoid duplicate
        query = template.replace("{kw}", random.choice(pool))
        query = f"{query} {random.randint(100, 999)}"
        self._used.add(query)
        return query

    def generate_batch(self, count: int, language: str = "mix") -> list[str]:
        """Generate `count` unique queries."""
        queries = []
        for _ in range(count):
            q = self.generate(language)
            if q not in queries:
                queries.append(q)
        random.shuffle(queries)
        return queries
