import base64
import logging
from aiogram import Router, F
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile, WebAppInfo
)
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import TARGET_INITIATIVE_URL, TARGET_INITIATIVE_ID, OFFICIAL_BOT_URL
from openbudget_api import OpenBudgetAPI, format_phone_number

logger = logging.getLogger(__name__)
router = Router()

class VoteState(StatesGroup):
    waiting_for_phone = State()
    waiting_for_captcha = State()
    waiting_for_otp = State()

def get_phone_keyboard() -> ReplyKeyboardMarkup:
    """Telefon raqamni yuborish tugmasi."""
    button = KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[button]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    return keyboard

def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Bekor qilish tugmasi."""
    button = KeyboardButton(text="❌ Bekor qilish")
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[button]],
        resize_keyboard=True
    )
    return keyboard

def get_inline_options_keyboard() -> InlineKeyboardMarkup:
    """Qo'shimcha rasmiy ovoz berish muqobil havolalari."""
    buttons = [
        [InlineKeyboardButton(text="🌐 Saytda ovoz berish (In-Telegram WebApp)", web_app=WebAppInfo(url=TARGET_INITIATIVE_URL))],
        [InlineKeyboardButton(text="🤖 Rasmiy Bot orqali ovoz berish", url=OFFICIAL_BOT_URL)]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """/start buyrug'i berilganda tashabbus va tugmalarni chiqaradi."""
    await state.clear()
    
    welcome_text = (
        f"<b>Assalomu alaykum!</b> 👋\n\n"
        f"Ushbu bot orqali <b>OpenBudget</b> loyihasidagi rasmiy mahallamiz tashabbusiga "
        f"veb-saytga kirmasdan ovoz berishingiz mumkin!\n\n"
        f"📌 <b>Tashabbusimiz:</b>\n"
        f"<i>G'afur G'ulom mahallasi 'Koinot' va 'Hurramlik' ko'chalarini asfalt qilish</i>\n\n"
        f"Ovoz berish uchun quyidagi <b>'📱 Telefon raqamni yuborish'</b> tugmasini bosing:"
    )
    
    await state.set_state(VoteState.waiting_for_phone)
    await message.answer(welcome_text, reply_markup=get_phone_keyboard(), parse_mode="HTML")
    await message.answer("Muqobil ovoz berish usullari:", reply_markup=get_inline_options_keyboard())

@router.message(F.text == "❌ Bekor qilish")
async def cancel_handler(message: Message, state: FSMContext):
    """Jarayonni bekor qilish."""
    await state.clear()
    await message.answer(
        "Ovoz berish bekor qilindi. Qayta boshlash uchun /start bosing.",
        reply_markup=ReplyKeyboardRemove()
    )

@router.message(VoteState.waiting_for_phone, F.contact)
async def process_contact(message: Message, state: FSMContext):
    """Telefon raqam qabul qilinib, CAPTCHA so'raladi."""
    phone_number = message.contact.phone_number
    clean_phone = format_phone_number(phone_number)
    
    await state.update_data(phone_number=clean_phone)
    await request_and_send_captcha(message, state)

@router.message(VoteState.waiting_for_phone, F.text)
async def process_phone_text(message: Message, state: FSMContext):
    """Telefon raqam matn ko'rinishida kiritilganda."""
    phone_text = message.text.strip()
    clean_phone = format_phone_number(phone_text)
    
    if len(clean_phone) != 12:
        await message.answer(
            "⚠️ Iltimos, pastdagi <b>'📱 Telefon raqamni yuborish'</b> tugmasini bosing "
            "yoki raqamingizni +998901234567 formatida kiriting.",
            reply_markup=get_phone_keyboard(),
            parse_mode="HTML"
        )
        return

    await state.update_data(phone_number=clean_phone)
    await request_and_send_captcha(message, state)

async def request_and_send_captcha(message: Message, state: FSMContext):
    """OpenBudget-dan Captcha rasmini olib foydalanuvchiga yuboradi."""
    wait_msg = await message.answer(
        "🔄 OpenBudget xavfsizlik CAPTCHA kodi olinmoqda...",
        reply_markup=ReplyKeyboardRemove()
    )
    
    success, captcha_key, captcha_img_base64, msg = await OpenBudgetAPI.get_captcha()
    
    if success and captcha_key:
        await state.update_data(captcha_key=captcha_key)
        await state.set_state(VoteState.waiting_for_captcha)
        
        # Base64 rasm bo'lsa, uni Telegram-ga rasm qilib yuboramiz
        if captcha_img_base64 and "," in captcha_img_base64:
            captcha_img_base64 = captcha_img_base64.split(",")[1]
            
        try:
            image_bytes = base64.b64decode(captcha_img_base64)
            photo = BufferedInputFile(image_bytes, filename="captcha.png")
            await message.answer_photo(
                photo=photo,
                caption="🔒 <b>SMS kod borishi uchun rasmdagi CAPTCHA kodini kiriting:</b>",
                reply_markup=get_cancel_keyboard(),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Captcha rasmini yuborishda xato: {e}")
            await message.answer(
                "Rasmdagi xavfsizlik kodini kiriting:",
                reply_markup=get_cancel_keyboard()
            )
    else:
        # Agar Captcha olinmasa, to'g'ridan-to'g'ri SMS so'rab ko'riladi yoki muqobil taklif qilinadi
        await message.answer(
            f"⚠️ OpenBudget serveriga ulanishda Captcha cheklovi yuz berdi.\n\n"
            f"SMS kod darhol borishi uchun quyidagi rasmiy usullardan birini bosing:",
            reply_markup=get_inline_options_keyboard()
        )

@router.message(VoteState.waiting_for_captcha, F.text)
async def process_captcha_input(message: Message, state: FSMContext):
    """Captcha kiritilgach, OpenBudget-ga SMS yuborish so'rovi beriladi."""
    captcha_result = message.text.strip()
    data = await state.get_data()
    phone_number = data.get("phone_number")
    captcha_key = data.get("captcha_key")
    
    await message.answer("🔄 Captcha tekshirilmoqda va SMS kod yuborilmoqda...")
    
    success, resp_msg, resp_data = await OpenBudgetAPI.request_otp(
        phone_number=phone_number,
        captcha_key=captcha_key,
        captcha_result=captcha_result,
        initiative_id=TARGET_INITIATIVE_ID
    )
    
    if success:
        await state.set_state(VoteState.waiting_for_otp)
        await message.answer(
            f"✅ <b>SMS kod yuborildi!</b>\n\n"
            f"Telefoningizga kelgan 6 xonali tasdiqlash kodini shu yerga kiriting:",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"❌ <b>Xatolik:</b> {resp_msg}\n\n"
            f"Captcha noto'g'ri bo'lsa, qayta urunish uchun /start bosing.",
            reply_markup=get_inline_options_keyboard()
        )

@router.message(VoteState.waiting_for_otp, F.text)
async def process_otp(message: Message, state: FSMContext):
    """SMS tasdiqlash kodi qabul qilinib ovoz beriladi."""
    otp_code = message.text.strip()
    
    if not otp_code.isdigit():
        await message.answer("⚠️ Iltimos, SMS orqali kelgan faqat raqamli kodni kiriting.")
        return
        
    data = await state.get_data()
    phone_number = data.get("phone_number")
    
    await message.answer("🔄 SMS kod tekshirilmoqda va ovoz berilmoqda...")
    
    success, resp_msg, resp_data = await OpenBudgetAPI.verify_otp(
        phone_number=phone_number,
        otp_code=otp_code,
        initiative_id=TARGET_INITIATIVE_ID
    )
    
    await state.clear()
    
    if success:
        await message.answer(
            f"🎉 <b>Ovozingiz muvaffaqiyatli qabul qilindi!</b>\n\n"
            f"Rahmat! Siz G'afur G'ulom mahallasi tashabbusiga ovoz berdingiz. 🙌",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"❌ <b>Xatolik:</b> {resp_msg}\n\nQayta urinish uchun /start bosing.",
            reply_markup=get_inline_options_keyboard(),
            parse_mode="HTML"
        )
