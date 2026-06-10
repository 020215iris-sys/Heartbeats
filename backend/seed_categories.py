"""
category_catalog 시드.

설문 카테고리(우울/불안/불면)와 절단점(severity_rule)을 민감 DB에 등록.
멱등: 여러 번 돌려도 안전(있으면 갱신, 없으면 삽입).
실행:  python seed_categories.py   (backend 폴더에서)
"""

import asyncio

from database import SessionLocalSensitive, engine_sensitive
from models import BaseSensitive, CategoryCatalog


CATEGORIES = [
    {
        "category_code": "depression",
        "display_name": "우울",
        "instrument": "PHQ-9",
        "instrument_ver": "1.0",
        "item_count": 9,
        "max_score": 27,
        "severity_rule": {
            "bands": [
                [0, 4, "없음", "none"],
                [5, 9, "낮음", "low"],
                [10, 14, "중간", "medium"],
                [15, 19, "약간높음", "medium_high"],
                [20, 27, "높음", "high"],
            ],
            "follow_up_codes": ["medium", "medium_high", "high"],
        },
    },
    {
        "category_code": "anxiety",
        "display_name": "불안",
        "instrument": "GAD-7",
        "instrument_ver": "1.0",
        "item_count": 7,
        "max_score": 21,
        "severity_rule": {
            "bands": [
                [0, 5, "없음", "none"],
                [6, 10, "낮음", "low"],
                [11, 15, "중간", "medium"],
                [16, 21, "높음", "high"],
            ],
            "follow_up_codes": ["medium", "high"],
        },
    },
    {
        "category_code": "insomnia",
        "display_name": "불면",
        "instrument": "KMISS",
        "instrument_ver": "1.0",
        "item_count": 3,
        "max_score": 30,
        "severity_rule": {
            "bands": [
                [0, 20, "불면 의심", "screen_positive"],
                [21, 30, "정상", "normal"],
            ],
            "follow_up_codes": ["screen_positive"],
        },
    },
]


async def seed():
    # 테이블 보장 (lifespan과 동일)
    async with engine_sensitive.begin() as conn:
        await conn.run_sync(BaseSensitive.metadata.create_all, checkfirst=True)

    async with SessionLocalSensitive() as session:
        for c in CATEGORIES:
            row = await session.get(CategoryCatalog, c["category_code"])
            if row is None:
                session.add(CategoryCatalog(**c))
            else:
                for key, val in c.items():
                    setattr(row, key, val)
        await session.commit()

    print("category_catalog 시드 완료:", [c["category_code"] for c in CATEGORIES])


if __name__ == "__main__":
    asyncio.run(seed())