temporary file

cyber_sentinel/
├── main.py                # Точка входа, инициализация приложения
├── core/                  # Ядро (логика сканирования)
│   ├── scanner.py         # ScannerEngine
│   ├── data_manager.py    # DataManager (настройки, история, монеты)
│   └── quarantine.py      # Логика работы с карантином
├── ui/                    # Графический интерфейс
│   ├── app.py             # Основной класс App (базовая настройка окна)
│   ├── sidebar.py         # Боковое меню и навигация
│   ├── dashboard.py       # Экран дашборда
│   └── ...                # Другие экраны (scanner_ui.py, settings_ui.py)
├── utils/                 # Вспомогательные функции
│   └── helpers.py         # Работа с хешами, системные проверки
└── resources/             # Конфиги и временные файлы
