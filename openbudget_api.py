import logging
import aiohttp
from typing import Dict, Any, Tuple
from config import API_SEND_CODE_URL, API_VERIFY_CODE_URL, TARGET_INITIATIVE_ID, OPENBUDGET_BASE_URL

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "uz,ru;q=0.9,en;q=0.8",
    "Origin": OPENBUDGET_BASE_URL,
    "Referer": f"{OPENBUDGET_BASE_URL}/",
    "Content-Type": "application/json"
}

def format_phone_number(phone: str) -> str:
    """Telefon raqamini 998XXXXXXXXX formatiga keltirish."""
    digits = ''.join(filter(str.isdigit, phone))
    if digits.startswith("998") and len(digits) == 12:
        return digits
    elif len(digits) == 9:
        return f"998{digits}"
    return digits

class OpenBudgetAPI:
    @staticmethod
    async def request_otp(phone_number: str, initiative_id: str = TARGET_INITIATIVE_ID) -> Tuple[bool, str, Dict[str, Any]]:
        """
        OpenBudget API ga ovoz berish uchun SMS OTP so'rovini yuboradi.
        """
        clean_phone = format_phone_number(phone_number)
        payload = {
            "phone": clean_phone,
            "initiativeId": initiative_id
        }

        logger.info(f"OTP so'rovi yuborilmoqda: phone={clean_phone}, initiativeId={initiative_id}")

        async with aiohttp.ClientSession(headers=HEADERS) as session:
            try:
                async with session.post(API_SEND_CODE_URL, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    data = await resp.json() if resp.content_type == 'application/json' else {}
                    if resp.status in (200, 201):
                        return True, "SMS kod telefon raqamingizga yuborildi.", data
                    else:
                        msg = data.get("message") or data.get("detail") or f"Xatolik yuz berdi ({resp.status})"
                        logger.warning(f"OTP jo'natishda xatolik: {resp.status} - {data}")
                        return False, msg, data
            except Exception as e:
                logger.error(f"OpenBudget API bop bog'lanishda xato: {e}")
                return False, f"Server bilan bog'lanishda xatolik: {str(e)}", {}

    @staticmethod
    async def verify_otp(phone_number: str, otp_code: str, initiative_id: str = TARGET_INITIATIVE_ID) -> Tuple[bool, str, Dict[str, Any]]:
        """
        OpenBudget API ga SMS tasdiqlash kodini yuborib, ovozni tasdiqlaydi.
        """
        clean_phone = format_phone_number(phone_number)
        payload = {
            "phone": clean_phone,
            "otp": otp_code.strip(),
            "initiativeId": initiative_id
        }

        logger.info(f"OTP tasdiqlash yuborilmoqda: phone={clean_phone}, otp={otp_code}")

        async with aiohttp.ClientSession(headers=HEADERS) as session:
            try:
                async with session.post(API_VERIFY_CODE_URL, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    data = await resp.json() if resp.content_type == 'application/json' else {}
                    if resp.status in (200, 201):
                        return True, "Ovozingiz muvaffaqiyatli qabul qilindi! Rahmat!", data
                    else:
                        msg = data.get("message") or data.get("detail") or "Kiritilgan SMS kod noto'g'ri yoki muddati o'tgan."
                        logger.warning(f"OTP tasdiqlashda xatolik: {resp.status} - {data}")
                        return False, msg, data
            except Exception as e:
                logger.error(f"OpenBudget API tasdiqlashda xato: {e}")
                return False, f"Server bilan bog'lanishda xatolik: {str(e)}", {}
