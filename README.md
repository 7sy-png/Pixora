<p align="center">
  <img src="app/resources/icons/pixora-logo.png" width="128" alt="Pixora">
</p>

<h1 align="center">PIXORA</h1>

<p align="center">
  Простая обработка изображений в нативном приложении для Windows.
</p>

<p align="center">
  <a href="https://github.com/7sy-png/Pixora/releases/latest/download/Pixora-v1.0.1-windows-x64.exe">
    <strong>Скачать Pixora для Windows</strong>
  </a>
</p>

![Главное окно Pixora](docs/screenshots/pixora-main.png)

## Возможности

- изменение ширины и высоты с сохранением пропорций;
- конвертация между JPEG, PNG и WEBP;
- настройка качества JPEG и WEBP;
- поворот на −90°, +90° и 180°;
- отражение по горизонтали и вертикали;
- Drag & Drop и выбор файла через проводник;
- предпросмотр результата перед сохранением;
- обработка без зависания интерфейса.

## Скачать и запустить

1. Скачайте
   [Pixora-v1.0.1-windows-x64.exe](https://github.com/7sy-png/Pixora/releases/latest/download/Pixora-v1.0.1-windows-x64.exe).
2. Запустите файл — установка не требуется.
3. Выберите изображение и задайте параметры обработки.

Сборка предназначена для 64-разрядных Windows 10 и Windows 11. При первом
запуске Windows может запросить подтверждение, так как приложение пока не
подписано коммерческим сертификатом.

## Использование

1. Перетащите изображение в окно или нажмите «Выбрать изображение».
2. Настройте размер, формат, поворот и отражение.
3. Нажмите «Обработать изображение».
4. Проверьте результат и сохраните его в выбранную папку.

![Результат обработки](docs/screenshots/pixora-result.png)

## Запуск из исходного кода

Понадобится Python 3.12 или новее.

```powershell
git clone https://github.com/7sy-png/Pixora.git
cd Pixora
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

Поддерживаются файлы `.jpg`, `.jpeg`, `.png` и `.webp` размером до 20 МБ.

## Лицензия

Проект распространяется по [лицензии MIT](LICENSE).
