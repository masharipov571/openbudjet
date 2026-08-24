import logging
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import TARGET_INITIATIVE_URL, TARGET_INITIATIVE_ID
from openbudget_api import OpenBudgetAPI, format_phone_number

logger = logging.getLogger(__name__)
router = Router()

class VoteState(StatesGroup):
    waiting_for_phone = State()
    waiting_for_otp = State()

def get_phone_keyboard() -> ReplyKeyboardMarkup:
    """Telefon raqamni yuborish tugmasi bo'lgan klaviatura."""
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

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """/start buyrug'i berilganda rasmiy tashabbus ma'lumotlarini ko'rsatadi."""
    await state.clear()
    
    welcome_text = (
        f"<b>Assalomu alaykum!</b> 👋\n\n"
        f"Ushbu bot orqali siz <b>OpenBudget</b> loyihasidagi rasmiy mahallamiz tashabbusiga "
        f"veb-saytga kirmasdan, bevosita bot ichida ovoz berishingiz mumkin.\n\n"
        f"📌 <b>Maqsadli tashabbus:</b>\n"
        f"<i>G'afur G'ulom mahallasining 'Koinot' va 'Hurramlik' ko'chalarini asfalt qilish</i>\n\n"
        f"🔗 <a href='{TARGET_INITIATIVE_URL}'>Tashabbus sahifasini ko'rish</a>\n\n"
        f"Ovoz berishni boshlash uchun quyidagi <b>'📱 Telefon raqamni yuborish'</b> tugmasini bosing:"
    )
    
    await state.set_state(VoteState.waiting_for_phone)
    await message.answer(welcome_text, reply_markup=get_phone_keyboard(), parse_mode="HTML")

@router.message(F.text == "❌ Bekor qilish")
async def cancel_handler(message: Message, state: FSMContext):
    """Jarayonni bekor qilish."""
    await state.clear()
    await message.answer(
        "Ovoz berish jarayoni bekor qilindi. Qayta boshlash uchun /start bosing.",
        reply_markup=ReplyKeyboardRemove()
    )

@router.message(VoteState.waiting_for_phone, F.contact)
async def process_contact(message: Message, state: FSMContext):
    """Telefon kontaktini qabul qilish va OpenBudget-ga SMS OTP so'rovi yuborish."""
    phone_number = message.contact.phone_number
    clean_phone = format_phone_number(phone_number)
    
    await state.update_data(phone_number=clean_phone)
    
    wait_msg = await message.answer(
        f"📱 Telefon raqamingiz ({clean_phone}) qabul qilindi.\n"
        f"OpenBudget tizimidan SMS tasdiqlash kodi yuborilmoqda, kuting...",
        reply_markup=ReplyKeyboardRemove()
    )
    
    # OpenBudget API ga SMS yuborish so'rovi
    success, resp_msg, data = await OpenBudgetAPI.request_otp(clean_phone, TARGET_INITIATIVE_ID)
    
    if success:
        await state.set_state(VoteState.waiting_for_otp)
        await message.answer(
            f"✅ <b>SMS kod yuborildi!</b>\n\n"
            f"Telefon raqamingizga kelgan 6 xonali tasdiqlash kodini shu yerga kiriting:",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
    else:
        await state.clear()
        await message.answer(
            f"❌ <b>Xatolik yuz berdi:</b>\n{resp_msg}\n\n"
            f"Qayta urinib ko'rish uchun /start tugmasini bosing.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="HTML"
        )

@router.message(VoteState.waiting_for_phone, F.text)
async def process_phone_text(message: Message, state: FSMContext):
    """Foydalanuvchi kontakt o'rniga telefon raqamini matn ko'rinishida kiritganda."""
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
    wait_msg = await message.answer(
        f"📱 Telefon raqam ({clean_phone}) qabul qilindi.\nSMS tasdiqlash kodi yuborilmoqda...",
        reply_markup=ReplyKeyboardRemove()
    )
    
    success, resp_msg, data = await OpenBudgetAPI.request_otp(clean_phone, TARGET_INITIATIVE_ID)
    
    if success:
        await state.set_state(VoteState.waiting_for_otp)
        await message.answer(
            f"✅ <b>SMS kod yuborildi!</b>\n\n"
            f"Telefon raqamingizga kelgan tasdiqlash kodini kiring:",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
    else:
        await state.clear()
        await message.answer(
            f"❌ <b>Xatolik yuz berdi:</b>\n{resp_msg}\n\n"
            f"Qayta urinish uchun /start bosing.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="HTML"
        )

@router.message(VoteState.waiting_for_otp, F.text)
async def process_otp(message: Message, state: FSMContext):
    """SMS tasdiqlash kodini qabul qilish va ovozni tasdiqlash."""
    otp_code = message.text.strip()
    
    if not otp_code.isdigit():
        await message.answer(
            "⚠️ Iltimos, faqat raqamlardan iborat SMS kodni kiriting (masalan: 123456)."
        )
        return
        
    data = await state.get_data()
    phone_number = data.get("phone_number")
    
    wait_msg = await message.answer("🔄 SMS kod tekshirilmoqda va ovoz berilmoqda...")
    
    success, resp_msg, resp_data = await OpenBudgetAPI.verify_otp(phone_number, otp_code, TARGET_INITIATIVE_ID)
    
    await state.clear()
    
    if success:
        success_text = (
            f"🎉 <b>Ovozingiz rasman qabul qilindi!</b>\n\n"
            f"Rahmat! Siz <i>G'afur G'ulom mahallasi 'Koinot' va 'Hurramlik' ko'chalarini asfalt qilish</i> "
            f"tashabbusini qo'llab-quvvatladingiz. 🙌\n\n"
            f"🔗 <a href='{TARGET_INITIATIVE_URL}'>Tashabbus natijasini kuzatish</a>"
        )
        await message.answer(success_text, reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
    else:
        fail_text = (
            f"❌ <b>Ovoz berish amalga oshmadi:</b>\n{resp_msg}\n\n"
            f"Qayta urinish uchun /start bosing."
        )
        await message.answer(fail_text, reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
