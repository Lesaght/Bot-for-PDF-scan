import logging
import os
import tempfile
import random
import string
import sqlite3
import shutil
from datetime import datetime
from threading import Timer

import img2pdf
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    CallbackQueryHandler
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

DB_NAME = 'user_data.db'
BACKUP_DIR = 'backups'
BACKUP_INTERVAL = 86400

translations = {
    'ru': {
        'start': "🔐 Введите проверочный код:",
        'verified': "✅ Вы уже прошли проверку! Можете отправлять изображения.",
        'code_message': "🔐 Проверочный код: <b>{code}</b>\n\nВведите этот код для подтверждения:\n—————————————\nОсталось попыток: {attempts}",
        'verification_passed': "✅ <b>Проверка пройдена!</b>\n\nТеперь вы можете отправлять изображения для преобразования в PDF.\nФормат: JPEG или PNG (как файл или фото).",
        'invalid_code': "❌ Неверный код! Осталось попыток: {attempts}\nПопробуйте еще раз: /start",
        'attempts_exceeded': "🚫 Лимит попыток исчерпан. Начните заново с /start",
        'help': "🖨️ <b>Бот для создания сканированных PDF-документов</b>\n\n✨ <b>Основные возможности:</b>\n- Проверка на бота через код\n- Преобразование фото/изображений в PDF\n- Улучшение качества: контраст + резкость\n\n📌 <b>Как использовать:</b>\n1. /start - начать и получить код\n2. Ввести полученный код\n3. Отправить изображение (фото или файл)\n4. Получить PDF-документ\n\n⚙️ Техническая поддержка: @your_support",
        'language_set': "🌍 Язык изменен на Русский",
        'lang_choose': "Выберите язык:",
        'need_verification': "⚠️ Сначала пройдите проверку через /start",
        'processing_error': "⚠️ Произошла ошибка при обработке изображения",
        'document_caption': "Ваш обработанный документ",
        'menu': "📂 Выберите действие:",
        'convert': "🖼️ Конвертировать",
        'settings': "⚙️ Настройки",
        'help_button': "❓ Помощь",
        'processing_start': "🔄 Изображение получено, начинаю конвертацию...",
        'choose_filter': "Выберите фильтр для обработки изображения:",
        'filter_bw': "Черно-белый",
        'filter_sepia': "Сепия",
        'filter_contrast': "Высокий контраст",
        'filter_sharpen': "Резкость",
        'filter_blur': "Размытие",
        'filter_grayscale': "Градации серого",
        'filter_invert': "Инверсия цветов",
        'filter_contour': "Контур",
        'filter_emboss': "Рельеф",
        'filter_detail': "Детализация",
        'filter_brightness': "Яркость",
        'filter_warm': "Теплые тона",
        'filter_cool': "Холодные тона",
        'filter_applied': "Фильтр выбран. Теперь отправьте изображение для обработки.",
        'settings_menu': "⚙️ Настройки:",
        'quality_settings': "Качество изображения",
        'pdf_format': "Формат PDF",
        'notifications': "Уведомления",
        'reset_settings': "Сбросить настройки",
        'quality_low': "Низкое",
        'quality_medium': "Среднее",
        'quality_high': "Высокое",
        'pdf_standard': "Стандартный",
        'pdf_compressed': "Сжатый",
        'notifications_on': "Включить",
        'notifications_off': "Отключить",
        'settings_reset': "Настройки сброшены."
    },
    'en': {
        'start': "🔐 Enter verification code:",
        'verified': "✅ You are already verified! You can send images.",
        'code_message': "🔐 Verification code: <b>{code}</b>\n\nEnter this code to confirm:\n—————————————\nAttempts left: {attempts}",
        'verification_passed': "✅ <b>Verification passed!</b>\n\nYou can now send images to convert to PDF.\nFormat: JPEG or PNG (as file or photo).",
        'invalid_code': "❌ Invalid code! Attempts left: {attempts}\nTry again: /start",
        'attempts_exceeded': "🚫 Attempt limit exceeded. Start over with /start",
        'help': "🖨️ <b>Scanned PDF Creation Bot</b>\n\n✨ <b>Main features:</b>\n- Bot verification via code\n- Convert photos/images to PDF\n- Quality enhancement: contrast + sharpness\n\n📌 <b>How to use:</b>\n1. /start - begin and get code\n2. Enter received code\n3. Send image (as photo or file)\n4. Receive PDF document\n\n⚙️ Technical support: @your_support",
        'language_set': "🌍 Language changed to English",
        'lang_choose': "Choose language:",
        'need_verification': "⚠️ First complete verification via /start",
        'processing_error': "⚠️ An error occurred while processing the image",
        'document_caption': "Your processed document",
        'menu': "📂 Choose action:",
        'convert': "🖼️ Convert",
        'settings': "⚙️ Settings",
        'help_button': "❓ Help",
        'processing_start': "🔄 Image received, starting conversion...",
        'choose_filter': "Choose a filter for image processing:",
        'filter_bw': "Black and White",
        'filter_sepia': "Sepia",
        'filter_contrast': "High Contrast",
        'filter_sharpen': "Sharpen",
        'filter_blur': "Blur",
        'filter_grayscale': "Grayscale",
        'filter_invert': "Invert Colors",
        'filter_contour': "Contour",
        'filter_emboss': "Emboss",
        'filter_detail': "Detail",
        'filter_brightness': "Brightness",
        'filter_warm': "Warm Tone",
        'filter_cool': "Cool Tone",
        'filter_applied': "Filter selected. Now send the image for processing.",
        'settings_menu': "⚙️ Settings:",
        'quality_settings': "Image Quality",
        'pdf_format': "PDF Format",
        'notifications': "Notifications",
        'reset_settings': "Reset Settings",
        'quality_low': "Low",
        'quality_medium': "Medium",
        'quality_high': "High",
        'pdf_standard': "Standard",
        'pdf_compressed': "Compressed",
        'notifications_on': "Enable",
        'notifications_off': "Disable",
        'settings_reset': "Settings have been reset."
    }
}


class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users
                         (user_id INTEGER PRIMARY KEY,
                          code TEXT,
                          verified INTEGER DEFAULT 0,
                          attempts INTEGER DEFAULT 3,
                          lang TEXT DEFAULT 'ru',
                          filter TEXT DEFAULT 'filter_bw',
                          quality INTEGER DEFAULT 95,
                          pdf_format TEXT DEFAULT 'standard',
                          notifications INTEGER DEFAULT 1)''')
        self.conn.commit()

    def get_user(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return cursor.fetchone()

    def update_user(self, user_id, **kwargs):
        cursor = self.conn.cursor()
        set_clause = ', '.join([f"{key} = ?" for key in kwargs])
        values = list(kwargs.values())
        values.append(user_id)
        cursor.execute(f'UPDATE users SET {set_clause} WHERE user_id = ?', values)
        self.conn.commit()

    def create_user(self, user_id, code, lang='ru'):
        cursor = self.conn.cursor()
        cursor.execute('''INSERT INTO users 
                          (user_id, code, lang) 
                          VALUES (?, ?, ?)''',
                       (user_id, code, lang))
        self.conn.commit()

    def backup(self):
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)

        backup_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copyfile(DB_NAME, os.path.join(BACKUP_DIR, backup_name))
        logger.info(f"Created backup: {backup_name}")

        Timer(BACKUP_INTERVAL, self.backup).start()


db = Database()
db.backup()


def get_translation(user_id: int, key: str, **kwargs) -> str:
    user = db.get_user(user_id)
    lang = user[4] if user else 'ru'
    return translations[lang].get(key, '').format(**kwargs)


async def language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Русский", callback_data='ru')],
        [InlineKeyboardButton("English", callback_data='en')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = get_translation(update.message.from_user.id, 'lang_choose')
    await update.message.reply_text(text, reply_markup=reply_markup)


async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    lang = query.data

    db.update_user(user_id, lang=lang)
    await query.answer()
    await query.edit_message_text(text=get_translation(user_id, 'language_set'))


async def show_menu(update: Update, user_id: int):
    keyboard = [
        [InlineKeyboardButton(get_translation(user_id, 'convert'), callback_data='convert')],
        [
            InlineKeyboardButton(get_translation(user_id, 'settings'), callback_data='settings'),
            InlineKeyboardButton(get_translation(user_id, 'help_button'), callback_data='help_menu')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        get_translation(user_id, 'menu'),
        reply_markup=reply_markup
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id

    if not db.get_user(user_id):
        code = ''.join(random.choices(string.digits, k=6))
        lang = 'ru'
        db.create_user(user_id, code, lang)

        await update.message.reply_text(
            get_translation(user_id, 'code_message', code=code, attempts=3),
            parse_mode='HTML'
        )
    else:
        user_data = db.get_user(user_id)
        if user_data[2]:  # verified
            await update.message.reply_text(get_translation(user_id, 'verified'))
            await show_menu(update, user_id)
        else:
            await update.message.reply_text(get_translation(user_id, 'need_verification'))


async def verify_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    text = update.message.text.strip()

    user_data = db.get_user(user_id)
    if not user_data:
        await update.message.reply_text(get_translation(user_id, 'need_verification'))
        return

    if user_data[2]:
        await update.message.reply_text(get_translation(user_id, 'verified'))
        return

    if text == user_data[1]:  # code
        db.update_user(user_id, verified=1)
        await update.message.reply_text(
            get_translation(user_id, 'verification_passed'),
            parse_mode='HTML'
        )
        await show_menu(update, user_id)
    else:
        attempts = user_data[3] - 1
        db.update_user(user_id, attempts=attempts)

        if attempts > 0:
            await update.message.reply_text(
                get_translation(user_id, 'invalid_code', attempts=attempts)
            )
        else:
            db.update_user(user_id, attempts=3, code='')
            await update.message.reply_text(get_translation(user_id, 'attempts_exceeded'))


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    await update.message.reply_text(
        get_translation(user_id, 'help'),
        parse_mode='HTML'
    )


async def settings_menu(update: Update, user_id: int):
    keyboard = [
        [InlineKeyboardButton(get_translation(user_id, 'language_set'), callback_data='language_settings')],
        [InlineKeyboardButton(get_translation(user_id, 'quality_settings'), callback_data='quality_settings')],
        [InlineKeyboardButton(get_translation(user_id, 'pdf_format'), callback_data='pdf_format')],
        [InlineKeyboardButton(get_translation(user_id, 'notifications'), callback_data='notifications')],
        [InlineKeyboardButton(get_translation(user_id, 'reset_settings'), callback_data='reset_settings')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(get_translation(user_id, 'settings_menu'), reply_markup=reply_markup)


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    action = query.data

    user_data = db.get_user(user_id)

    if not user_data or not user_data[2]:  # user_data[2] - это поле verified
        await query.message.reply_text(get_translation(user_id, 'need_verification'))
        await query.answer()
        return

    if action == 'convert':
        keyboard = [
            [InlineKeyboardButton(get_translation(user_id, 'filter_bw'), callback_data='filter_bw')],
            [InlineKeyboardButton(get_translation(user_id, 'filter_sepia'), callback_data='filter_sepia')],
            [InlineKeyboardButton(get_translation(user_id, 'filter_contrast'), callback_data='filter_contrast')],
            [InlineKeyboardButton(get_translation(user_id, 'filter_sharpen'), callback_data='filter_sharpen')],
            [InlineKeyboardButton(get_translation(user_id, 'filter_blur'), callback_data='filter_blur')],
            [InlineKeyboardButton(get_translation(user_id, 'filter_grayscale'), callback_data='filter_grayscale')],
            [InlineKeyboardButton(get_translation(user_id, 'filter_invert'), callback_data='filter_invert')],
            [InlineKeyboardButton(get_translation(user_id, 'filter_contour'), callback_data='filter_contour')],
            [InlineKeyboardButton(get_translation(user_id, 'filter_emboss'), callback_data='filter_emboss')],
            [InlineKeyboardButton(get_translation(user_id, 'filter_detail'), callback_data='filter_detail')],
            [InlineKeyboardButton(get_translation(user_id, 'filter_brightness'), callback_data='filter_brightness')],
            [InlineKeyboardButton(get_translation(user_id, 'filter_warm'), callback_data='filter_warm')],
            [InlineKeyboardButton(get_translation(user_id, 'filter_cool'), callback_data='filter_cool')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(get_translation(user_id, 'choose_filter'), reply_markup=reply_markup)
    elif action == 'settings':
        await settings_menu(query, user_id)
    elif action == 'help_menu':
        await help_command(query, context)

    await query.answer()


async def filter_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    filter_type = query.data

    db.update_user(user_id, filter=filter_type)
    await query.answer()
    await query.edit_message_text(text=get_translation(user_id, 'filter_applied'))


async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    action = query.data

    if action == 'language_settings':
        await language(query, context)
    elif action == 'quality_settings':
        keyboard = [
            [InlineKeyboardButton(get_translation(user_id, 'quality_low'), callback_data='quality_low')],
            [InlineKeyboardButton(get_translation(user_id, 'quality_medium'), callback_data='quality_medium')],
            [InlineKeyboardButton(get_translation(user_id, 'quality_high'), callback_data='quality_high')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(get_translation(user_id, 'quality_settings'), reply_markup=reply_markup)
    elif action == 'pdf_format':
        keyboard = [
            [InlineKeyboardButton(get_translation(user_id, 'pdf_standard'), callback_data='pdf_standard')],
            [InlineKeyboardButton(get_translation(user_id, 'pdf_compressed'), callback_data='pdf_compressed')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(get_translation(user_id, 'pdf_format'), reply_markup=reply_markup)
    elif action == 'notifications':
        keyboard = [
            [InlineKeyboardButton(get_translation(user_id, 'notifications_on'), callback_data='notifications_on')],
            [InlineKeyboardButton(get_translation(user_id, 'notifications_off'), callback_data='notifications_off')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(get_translation(user_id, 'notifications'), reply_markup=reply_markup)
    elif action == 'reset_settings':
        db.update_user(user_id, quality=95, pdf_format='standard', notifications=1)
        await query.message.reply_text(get_translation(user_id, 'settings_reset'))
    elif action in ['quality_low', 'quality_medium', 'quality_high']:
        # Обработка выбора качества
        quality_map = {
            'quality_low': 75,
            'quality_medium': 85,
            'quality_high': 95
        }
        quality_value = quality_map.get(action, 95)
        db.update_user(user_id, quality=quality_value)
        await query.answer()
        await query.edit_message_text(text=get_translation(user_id, 'settings_menu'))
    elif action in ['pdf_standard', 'pdf_compressed']:
        # Обработка выбора формата PDF
        pdf_format_map = {
            'pdf_standard': 'standard',
            'pdf_compressed': 'compressed'
        }
        pdf_format_value = pdf_format_map.get(action, 'standard')
        db.update_user(user_id, pdf_format=pdf_format_value)
        await query.answer()
        await query.edit_message_text(text=get_translation(user_id, 'settings_menu'))

    await query.answer()


def apply_filter(image: Image.Image, filter_type: str) -> Image.Image:
    if filter_type == 'filter_bw':
        return image.convert('L')
    elif filter_type == 'filter_sepia':
        sepia = image.convert('RGB')
        width, height = sepia.size
        pixels = sepia.load()
        for py in range(height):
            for px in range(width):
                r, g, b = sepia.getpixel((px, py))
                tr = int(0.393 * r + 0.769 * g + 0.189 * b)
                tg = int(0.349 * r + 0.686 * g + 0.168 * b)
                tb = int(0.272 * r + 0.534 * g + 0.131 * b)
                pixels[px, py] = (min(tr, 255), min(tg, 255), min(tb, 255))
        return sepia
    elif filter_type == 'filter_contrast':
        enhancer = ImageEnhance.Contrast(image)
        return enhancer.enhance(2.0)
    elif filter_type == 'filter_sharpen':
        return image.filter(ImageFilter.SHARPEN)
    elif filter_type == 'filter_blur':
        return image.filter(ImageFilter.BLUR)
    elif filter_type == 'filter_grayscale':
        return image.convert('L')
    elif filter_type == 'filter_invert':
        return ImageOps.invert(image.convert('RGB'))
    elif filter_type == 'filter_contour':
        return image.filter(ImageFilter.CONTOUR)
    elif filter_type == 'filter_emboss':
        return image.filter(ImageFilter.EMBOSS)
    elif filter_type == 'filter_detail':
        return image.filter(ImageFilter.DETAIL)
    elif filter_type == 'filter_brightness':
        enhancer = ImageEnhance.Brightness(image)
        return enhancer.enhance(1.5)
    elif filter_type == 'filter_warm':
        enhancer = ImageEnhance.Color(image)
        return enhancer.enhance(1.5)
    elif filter_type == 'filter_cool':
        enhancer = ImageEnhance.Color(image)
        return enhancer.enhance(0.5)
    else:
        return image


async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id

    user_data = db.get_user(user_id)
    if not user_data or not user_data[2]:  # verified
        await update.message.reply_text(get_translation(user_id, 'need_verification'))
        return

    await update.message.reply_text(get_translation(user_id, 'processing_start'))

    with tempfile.TemporaryDirectory() as tmp_dir:
        try:
            if update.message.photo:
                file = await update.message.photo[-1].get_file()
            else:
                file = await update.message.document.get_file()

            input_path = os.path.join(tmp_dir, 'input_image')
            await file.download_to_drive(input_path)

            filter_type = user_data[5] if user_data else 'filter_bw'
            processed_image = process_image(input_path, filter_type)
            processed_path = os.path.join(tmp_dir, 'processed.jpg')

            quality = user_data[6] if user_data else 95
            processed_image.save(processed_path, 'JPEG', quality=quality)

            pdf_path = os.path.join(tmp_dir, 'document.pdf')
            with open(pdf_path, 'wb') as f:
                f.write(img2pdf.convert(processed_path))

            await update.message.reply_document(
                document=open(pdf_path, 'rb'),
                caption=get_translation(user_id, 'document_caption'),
                filename='document.pdf'
            )

        except Exception as e:
            logger.error(f"Image processing error: {e}")
            await update.message.reply_text(get_translation(user_id, 'processing_error'))


def process_image(image_path: str, filter_type: str) -> Image.Image:
    with Image.open(image_path) as img:
        img = apply_filter(img, filter_type)
        return img


def main():
    TOKEN = "your_bot_token"

    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("language", language))

    application.add_handler(CallbackQueryHandler(language_callback, pattern='^(ru|en)$'))
    application.add_handler(CallbackQueryHandler(menu_callback, pattern='^(convert|settings|help_menu)$'))

    application.add_handler(CallbackQueryHandler(filter_callback,
                                                 pattern='^(filter_bw|filter_sepia|filter_contrast|filter_sharpen|filter_blur|filter_grayscale|filter_invert|filter_contour|filter_emboss|filter_detail|filter_brightness|filter_warm|filter_cool)$'))

    application.add_handler(CallbackQueryHandler(settings_callback,
                                                 pattern='^(language_settings|quality_settings|pdf_format|notifications|reset_settings|quality_low|quality_medium|quality_high|pdf_standard|pdf_compressed|notifications_on|notifications_off)$'))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, verify_code))
    application.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_image))

    application.run_polling()


if __name__ == '__main__':
    main()