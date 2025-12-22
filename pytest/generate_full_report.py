#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт для генерации полного отчета по всем тестам проекта.
Создает единый HTML отчет со всеми тестами из папки pytests/.
"""

import subprocess  # Для выполнения команд pytest
import sys  # Для работы с аргументами командной строки
import os  # Для работы с путями и файлами
from datetime import datetime  # Для добавления временных меток

# Настройка кодировки для Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Добавляем корневую директорию проекта в PYTHONPATH для импорта модулей проекта
# Скрипт находится в pytest/, поэтому нужно подняться на уровень выше
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)  # Корень проекта (на уровень выше pytest/)
current_dir = project_root
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
# Устанавливаем PYTHONPATH для подпроцесса pytest
os.environ['PYTHONPATH'] = current_dir + os.pathsep + os.environ.get('PYTHONPATH', '')


def generate_full_test_report():
    """
    Генерирует полный HTML отчет по всем тестам проекта.
    Создает файл 'full_test_report.html' в папке test_reports/.
    """
    # Создаем папку для отчетов если её нет (в корне проекта)
    reports_dir = os.path.join(project_root, "test_reports")
    if not os.path.exists(reports_dir):
        os.makedirs(reports_dir)
        print(f"✓ Создана папка для отчетов: {reports_dir}")
    
    # Имя файла для полного отчета
    report_file = os.path.join(reports_dir, "full_test_report.html")
    
    # Формируем команду pytest для запуска всех тестов
    pytest_args = [
        "pytest",  # Команда pytest
        "pytests/",  # Запускаем все тесты из папки pytests
        "--html=" + report_file,  # Путь к выходному HTML файлу
        "--self-contained-html",  # Включить CSS/JS прямо в HTML (один файл)
        "--verbose",  # Подробный вывод
        "--tb=short",  # Краткий traceback при ошибках
        "--durations=20",  # Показать 20 самых медленных тестов
        "-v",  # Еще более подробный вывод
    ]
    
    # Добавляем дополнительные аргументы из командной строки
    if len(sys.argv) > 1:
        pytest_args.extend(sys.argv[1:])
    
    print("=" * 70)
    print(" ГЕНЕРАЦИЯ ПОЛНОГО ОТЧЕТА ПО ВСЕМ ТЕСТАМ")
    print("=" * 70)
    print(f" Отчет будет сохранен в: {report_file}")
    print(f" Папка с тестами: pytests/")
    print(f" Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()
    
    # Запускаем pytest из корневой директории проекта
    result = subprocess.run(pytest_args, cwd=project_root)
    
    print()
    print("=" * 70)
    if result.returncode == 0:
        print(" Все тесты пройдены успешно!")
    else:
        print(" Некоторые тесты завершились с ошибками")
    
    # Проверяем что HTML отчет был создан
    if os.path.exists(report_file):
        file_size = os.path.getsize(report_file) / 1024  # Размер в KB
        print(f" Полный отчет сохранен: {report_file}")
        print(f" Размер файла: {file_size:.2f} KB")
        print()
        print(" Для просмотра отчета откройте файл в браузере:")
        print(f"   {os.path.abspath(report_file)}")
    else:
        print(f"  HTML отчет НЕ был создан (возможна ошибка импорта модулей)")
        print(f"   Проверьте что все зависимости установлены: pip install -r requirements.txt")
    
    print("=" * 70)
    print()
    
    return result.returncode


if __name__ == "__main__":
    # Выводим справку если запрошена
    if "--help" in sys.argv or "-h" in sys.argv:
        print("""
Использование:
    python generate_full_report.py [pytest опции]

Описание:
    Генерирует полный HTML отчет по всем тестам проекта.
    Отчет сохраняется в test_reports/full_test_report.html

Примеры:
    # Базовый запуск (все тесты)
    python generate_full_report.py
    
    # С покрытием кода
    python generate_full_report.py --cov=. --cov-report=html
    
    # Только определенные маркеры
    python generate_full_report.py -m "not slow"
    
    # С дополнительной детализацией
    python generate_full_report.py -vv

Результат:
    test_reports/full_test_report.html - полный отчет по всем тестам
        """)
        sys.exit(0)
    
    # Запускаем генерацию отчета
    exit_code = generate_full_test_report()
    sys.exit(exit_code)

