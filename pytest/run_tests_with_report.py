#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт для запуска тестов с автоматической генерацией HTML отчета.
Использует pytest-html для создания красивого интерактивного отчета.
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


def run_tests_with_html_report():
    """
    Запускает pytest с генерацией HTML отчета.
    
    Создает папку 'test_reports' если её нет, и генерирует отчет
    с временной меткой в названии файла.
    """
    # Создаем папку для отчетов если её нет (в корне проекта)
    reports_dir = os.path.join(project_root, "test_reports")
    if not os.path.exists(reports_dir):
        os.makedirs(reports_dir)
        print(f"✓ Создана папка для отчетов: {reports_dir}")
    
    # Генерируем имя файла с временной меткой
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = os.path.join(reports_dir, f"test_report_{timestamp}.html")
    
    # Формируем команду pytest с опциями для HTML отчета
    # Меняем рабочую директорию на корень проекта для запуска pytest
    pytest_args = [
        "pytest",  # Команда pytest
        "--html=" + report_file,  # Путь к выходному HTML файлу
        "--self-contained-html",  # Включить CSS/JS прямо в HTML (один файл)
        "--verbose",  # Подробный вывод
        "--tb=short",  # Краткий traceback при ошибках
        "--durations=10",  # Показать 10 самых медленных тестов
    ]
    
    # Добавляем дополнительные аргументы из командной строки
    if len(sys.argv) > 1:
        pytest_args.extend(sys.argv[1:])
    
    print("=" * 70)
    print("Запуск тестов с генерацией HTML отчета...")
    print("=" * 70)
    print(f" Отчет будет сохранен в: {report_file}")
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
        print(f"HTML отчет сохранен: {report_file}")
        
        # Создаем копию последнего отчета для удобства
        latest_report = os.path.join(reports_dir, "latest_report.html")
        if os.path.exists(latest_report):
            os.remove(latest_report)
        
        # На Windows используем copy вместо symlink
        if os.name == 'nt':  # Windows
            import shutil
            shutil.copy2(report_file, latest_report)
        else:  # Linux/Mac
            os.symlink(os.path.basename(report_file), latest_report)
        
        print(f"🔗 Быстрый доступ к последнему отчету: {latest_report}")
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
    python run_tests_with_report.py [pytest опции]

Примеры:
    # Запустить все тесты
    python run_tests_with_report.py
    
    # Запустить только тесты чата
    python run_tests_with_report.py pytests/test_chat.py
    
    # Запустить с покрытием кода
    python run_tests_with_report.py --cov=. --cov-report=html
    
    # Запустить только помеченные тесты
    python run_tests_with_report.py -m chat
    
    # Запустить конкретный тест
    python run_tests_with_report.py pytests/test_chat.py::test_chat_create_task_success

HTML отчет будет автоматически сохранен в папке test_reports/
        """)
        sys.exit(0)
    
    # Запускаем тесты
    exit_code = run_tests_with_html_report()
    sys.exit(exit_code)

