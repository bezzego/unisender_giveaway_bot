from __future__ import annotations

from dataclasses import dataclass
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.repositories.participants import ParticipantRepo
from app.repositories.promo_codes import PromoCodeRepo


log = logging.getLogger(__name__)

WINNER_PROMO_PLACEHOLDER = "ХХХХХХХХ"

WINNER_MESSAGE_TEMPLATE = (
    "Спасибо, что подписались на нашу рассылку! Делимся промокодом для посещения кинотеатра 🔽\n\n"
    "{promo_code}\n\n"
    "Правила пользования:\n"
    "1 код = 1 пригласительный (1 билет)\n\n"
    "В кассе кинотеатра выберите сеанс и места в зале, продиктуйте кассиру 10-ти значный код, получите билет.\n\n"
    "Код ДЕЙСТВУЕТ:\n"
    "- До 1 июня 2026 года (кроме 1-11 января)\n"
    "- В любой день недели\n"
    "- Во кинотеатрах сети КИНО ОККО «Синема Парк» и «Формула Кино», полный перечень кинотеатров на сайте: <a href=\"https://kinoteatr.ru/\">https://kinoteatr.ru/</a> (кроме к-т Родина в Казани, это франшиза)\n"
    "- На сеансы в формате 2D и 3D\n"
    "- На показы в обычных залах, а также в залах Dolby Atmos\n\n"
    "ОГРАНИЧЕНИЯ:\n"
    "Действие кода не распространяется на:\n"
    "- Форматы IMAX, IMAX Sapphire, 4D и 4DX, залы повышенной комфортности (VIP, RELAX, JOLLY, Business, Premium), залы «Мувик» и KIDS\n"
    "- На показы альтернативного контента (трансляции оперных спектаклей, балета, спортивных мероприятий, фестивальных фильмов, фильмов-концертов и т.д.)\n\n"
    "Код может быть использован только один раз.\n\n"
    "Для просмотра сеансов в формате 3D необходимы специальные очки, которые можно дополнительно приобрести в кассах кинотеатрах."
)

NON_WINNER_MESSAGE_TEMPLATE = (
    "Спасибо, что подписались на нашу рассылку! К сожалению, разыгрываемые нами билеты в кино закончились, но мы дарим вам большой гид по петербургским театрам (<a href=\"{guide_link}\">{guide_link}</a>). "
    "В нём мы рассказали, что смотреть в этом сезоне на 20 городских сценах — от крупных и известных до камерных и независимых."
)


@dataclass(frozen=True)
class RewardResult:
    reward_type: str  # cinema|guide|promo
    promo_code: str | None
    message: str


class RewardService:
    @staticmethod
    def render_message(reward_type: str, promo_code: str | None) -> str:
        log.debug("Rendering reward message", extra={"reward_type": reward_type})
        if reward_type in {"cinema", "promo"}:
            code = promo_code or WINNER_PROMO_PLACEHOLDER
            return WINNER_MESSAGE_TEMPLATE.format(promo_code=code)
        if reward_type == "guide":
            return NON_WINNER_MESSAGE_TEMPLATE.format(guide_link=settings.guide_link)
        return NON_WINNER_MESSAGE_TEMPLATE.format(guide_link=settings.guide_link)

    @staticmethod
    async def assign_reward(session: AsyncSession, participant_id: int) -> RewardResult:
        """
        Must be called inside a DB transaction.
        Priority:
        1) cinema if winners < limit AND there is free cinema code
        2) promo if FALLBACK_PROMO set
        3) guide
        """
        log.info("Assigning reward", extra={"participant_id": participant_id})
        winners = await ParticipantRepo.count_cinema_winners(session)
        log.debug("Cinema winners count", extra={"winners": winners, "limit": settings.cinema_limit})
        if winners < settings.cinema_limit:
            code = await PromoCodeRepo.get_free_code_for_update(session, kind="cinema")
            if code:
                log.info("Cinema promo code assigned", extra={"promo_code_id": code.id})
                await PromoCodeRepo.mark_used(session, promo_code_id=code.id, participant_id=participant_id)
                return RewardResult(
                    reward_type="cinema",
                    promo_code=code.code,
                    message=RewardService.render_message("cinema", code.code),
                )

        if settings.fallback_promo:
            log.warning("Cinema limit reached or no codes; using fallback promo", extra={"participant_id": participant_id})
            return RewardResult(
                reward_type="promo",
                promo_code=settings.fallback_promo,
                message=RewardService.render_message("promo", settings.fallback_promo),
            )

        log.warning("Cinema limit reached or no codes; using guide", extra={"participant_id": participant_id})
        return RewardResult(
            reward_type="guide",
            promo_code=None,
            message=RewardService.render_message("guide", None),
        )
