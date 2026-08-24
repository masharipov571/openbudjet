import logging
import aiohttp
from typing import Dict, Any, Tuple, Optional
from config import OPENBUDGET_BASE_URL, TARGET_INITIATIVE_ID

logger = logging.getLogger(__name__)

API_CAPTCHA_URL = f"{OPENBUDGET_BASE_URL}/api/v1/user/temp/captcha"
API_SEND_CODE_URL = f"{OPENBUDGET_BASE_URL}/api/v1/user/temp/vote"
API_VERIFY_CODE_URL = f"{OPENBUDGET_BASE_URL}/api/v1/user/temp/vote/verify"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
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
    async def get_captcha() -> Tuple[bool, Optional[str], Optional[str], str]:
        """
        OpenBudget API dan CAPTCHA rasmi (base64) va captchaKey ni oladi.
        Returns: (success, captcha_key, base64_image, message)
        """
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            try:
                async with session.get(API_CAPTCHA_URL, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        key = data.get("key") or data.get("captchaKey")
                        img = data.get("image") or data.get("captcha")
                        return True, key, img, "CAPTCHA olindi."
                    else:
                        return False, None, None, f"CAPTCHA olishda xatolik ({resp.status})"
            except Exception as e:
                logger.error(f"CAPTCHA olishda xato: {e}")
                return False, None, None, f"Serverga bog'lanishda xatolik: {str(e)}"

    @staticmethod
    async def request_otp(
        phone_number: str, 
        captcha_key: str, 
        captcha_result: str, 
        initiative_id: str = TARGET_INITIATIVE_ID
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        OpenBudget API ga Captcha bilan SMS OTP so'rovini yuboradi.
        """
        clean_phone = format_phone_number(phone_number)
        payload = {
            "phone": clean_phone,
            "initiativeId": initiative_id,
            "captchaKey": captcha_key,
            "captchaResult": captcha_result.strip()
        }

        logger.info(f"OTP so'rovi (Captcha bilan) yuborilmoqda: phone={clean_phone}")

        async with aiohttp.ClientSession(headers=HEADERS) as session:
            try:
                async with session.post(API_SEND_CODE_URL, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    data = await resp.json() if resp.content_type == 'application/json' else {}
                    if resp.status in (200, 201):
                        return True, "SMS tasdiqlash kodi telefon raqamingizga yuborildi.", data
                    else:
                        msg = data.get("message") or data.get("detail") or f"CAPTCHA yoki ma'lumot xatosi ({resp.status})"
                        logger.warning(f"OTP jo'natishda xatolik: status={resp.status}, data={data}")
                        return False, msg, data
            except Exception as e:
                logger.error(f"OpenBudget API bog'lanishda xato: {e}")
                return False, f"Server bilan bog'lanishda xatolik: {str(e)}", {}

    @staticmethod
    async def verify_otp(
        phone_number: str, 
        otp_code: str, 
        initiative_id: str = TARGET_INITIATIVE_ID
    ) -> Tuple[bool, str, Dict[str, Any]]:
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
                        return True, "Ovozingiz muvaffaqiyatli qabul qilindi!", data
                    else:
                        msg = data.get("message") or data.get("detail") or "SMS kod noto'g'ri yoki muddati o'tgan."
                        logger.warning(f"OTP tasdiqlashda xatolik: status={resp.status}, data={data}")
                        return False, msg, data
            except Exception as e:
                logger.error(f"OpenBudget API tasdiqlashda xato: {e}")
                return False, f"Server bilan bog'lanishda xatolik: {str(e)}", {}
