import glob
from playwright.async_api import async_playwright
import os
import pickle
import logging
from jsons import var2, var, devices
import asyncio

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,  # Устанавливаем уровень логирования
    format='%(asctime)s - %(levelname)s - %(message)s',  # Формат сообщения
    handlers=[
        logging.FileHandler("log/app.log"),  # Записывать в файл
        logging.StreamHandler()  # Также выводить в консоль
    ]
)
class Parse:
    def __init__(self):
        self.download_path = "tables/"

    def delete_files(self):
        """Удаление файлов из папки."""
        files_to_delete = glob.glob(os.path.join(self.download_path, '*'))
        for file in files_to_delete:
            if not file.endswith('.xlsx'):
                try:
                    os.remove(file)
                    logging.info(f"Файл {file} удалён.")
                except Exception as e:
                    logging.error(f"Не удалось удалить файл {file}: {e}")

    async def parse_button(self, p, page, file_name):
        self.file_name = file_name
        await page.wait_for_selector('.StarTable-Body')
        logging.info('Страница загружена, ожидаем селектор .StarTable-Body')

        async def on_download(download, file_name):
            await download.save_as(os.path.join(self.download_path, file_name))

        page.on('download', lambda download: on_download(download, file_name=f'{self.file_name.strip()}.xlsx'))
        await page.click(".g-button_pin_round-round.DownloaderButton")
        await page.wait_for_timeout(3000)
        self.delete_files()


class Browser(Parse):
    def __init__(self):
        super().__init__()
        self.new_page = None
        self.page = None
        self.url2 = None
        self.cookie_file = 'cookie/cookies.pkl'
        self.ready = False

    async def control_app(self, keywords: list, device: str, region: int):
        self.keywords = keywords
        self.device = device
        self.region = region
        self.ready = False
        logging.info("Запускаем обработку ключевых слов...")

        async with async_playwright() as p:
            logging.info("Запуск браузера...")
            browser = await self.start_browser(p, headless=False)
            logging.info("Браузер запущен")
            self.page = await browser.new_page()
            if await self.registration(self.page) == 1:
                logging.info('Авторизация прошла успешно.')
                self.ready = True
                await browser.close()
        if self.ready:

            for keyword in self.keywords:
                self.url2 = (
                    f"https://webmaster.yandex.ru/site/efficiency/wordcraft/?device={self.device}&query={keyword}"
                    f"&userQueries=SITES&rivals=GENERAL&tab=GENERAL&regions={self.region}")
                try:
                    async with async_playwright() as v:
                        browser = await self.start_browser(v, headless=True)
                        self.new_page = await browser.new_page()
                        await self.registration(self.new_page)
                        try:
                            await self.new_page.goto(self.url2, timeout=30000)  # Установить тайм-аут 30 секунд
                        except Exception as e:
                            logging.error(f"Ошибка при переходе по URL: {e}")
                        await self.parse_button(v, self.new_page, keyword)
                except Exception as e:
                    logging.error(f"Ошибка при обработке ключевого слова '{keyword}': {e}")

    async def start_browser(self, p, headless=True, download_path='tables/'):
        try:
            chromium = await p.chromium.launch(headless=headless, downloads_path=download_path)
            logging.info("Chromium успешно запущен")
            return chromium
        except Exception as e:
            logging.error(f"Ошибка при запуске Chromium: {e}")
        try:
            firefox = p.firefox.launch(headless=headless, downloads_path=download_path)
            logging.info("Firefox успешно запущен")
            return firefox
        except Exception as e:
            logging.error(f"Ошибка при запуске Firefox: {e}")
        try:
            webkit = p.webkit.launch(headless=headless, downloads_path=download_path)
            logging.info("WebKit (Safari) успешно запущен")
            return webkit
        except Exception as e:
            logging.error(f"Ошибка при запуске WebKit: {e}")
        logging.error("Не удалось запустить браузер. Попробуйте другой.")
        return None

    async def cookie_save(self, page):
        """Сохранение cookies."""
        cookies = await page.context.cookies()
        with open(self.cookie_file, 'wb') as f:
            pickle.dump(cookies, f)
        logging.info("Куки сохранены.")

    async def registration(self, page):
        if os.path.exists(self.cookie_file):
            with open(self.cookie_file, 'rb') as f:
                cookies = pickle.load(f)
                for cookie in cookies:
                    await page.context.add_cookies([cookie])
                await self.cookie_save(page)
                logging.info("Используем сохранённые куки для авторизации.")
                return 1
        else:
            await self.page.goto("https://passport.yandex.ru/auth")
            await self.page.wait_for_url("https://id.yandex.ru/", timeout=60000)
            cookies = await page.context.cookies()
            with open(self.cookie_file, 'wb') as f:
                pickle.dump(cookies, f)
            logging.info("Новые куки сохранены.")
            await self.registration(page)


async def ask_user_input():
    for idx, region in enumerate(var.keys(), 1):
        print(f"{idx}: {region}")

    # Запрашиваем выбор региона
    region_choice = int(input("Введите номер региона: "))
    region_number = var2.get(region_choice)
    region_number = var.get(region_number)
    # Запрашиваем ключевые слова
    keywords = input("Введите ключевые слова, разделённые запятыми: ")
    keywords2 = list(map(str, keywords.strip().split(',')))

    device = int(input("Введите устройство (Все устройства(1), Только компьютер(2), Только компьютеры(3)): "))
    device = devices.get(device)

    return keywords2, device, region_number


async def main():
    keywords, device, region = await ask_user_input()
    logging.info(f'device:{device}')
    logging.info(f'region:{region}')
    logging.info(f'keywords:{keywords}')
    logging.info(f"Вы выбрали регион: {region}")
    logging.info(f"Ключевые слова: {keywords}")
    logging.info(f"Устройство: {device}")
    # Запускаем парсинг с введёнными данными
    await Browser().control_app(keywords, device, region)


# Запуск основного приложения
if __name__ == "__main__":
    asyncio.run(main())
