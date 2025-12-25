from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db import SessionMaker
from app.models import PromoCode


logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
log = logging.getLogger(__name__)


RAW_CODES = """
80  88151262
80  88151381
80  88151464
80  88151546
80  88151619
80  88151752
80  88151818
80  88151999
80  88152022
80  88152185
80  88152279
80  88152316
80  88152497
80  88152510
80  88152676
80  88152762
80  88152874
80  88152917
80  88153040
80  88153110
80  88153221
80  88153341
80  88153477
80  88153522
80  88153647
80  88153787
80  88153822
80  88153930
80  88154078
80  88154166
80  88154273
80  88154350
80  88154433
80  88154563
80  88154632
80  88154727
80  88154885
80  88154948
80  88155054
80  88155123
""".strip()


def parse_codes(raw: str) -> list[str]:
    codes: list[str] = []
    for line in raw.splitlines():
        parts = line.strip().split()
        if not parts:
            continue
        if len(parts) == 1:
            code = parts[0]
        else:
            code = "".join(parts)
        codes.append(code)
    return codes


async def insert_codes(codes: list[str]) -> None:
    async with SessionMaker() as session:
        async with session.begin():
            existing = await session.execute(select(PromoCode.code))
            existing_codes = {row[0] for row in existing.fetchall()}

            to_insert = [code for code in codes if code not in existing_codes]
            for code in to_insert:
                session.add(PromoCode(kind="cinema", code=code))

    log.info("Promo codes inserted", extra={"total": len(codes), "inserted": len(to_insert)})


if __name__ == "__main__":
    codes_list = parse_codes(RAW_CODES)
    asyncio.run(insert_codes(codes_list))
