import os
from fastapi.testclient import TestClient
from sqlalchemy import text
from unittest.mock import patch
import pytest
from datetime import datetime
import platform

os.environ["TESTING"] = "true"

from database import Base
from db import engine
from main import app


# ============= Хуки для кастомизации pytest-html отчетов =============

def pytest_configure(config):
    """
    Добавляет метаданные в HTML отчет при инициализации pytest.
    Вызывается один раз в начале сессии тестирования.
    """
    # Проверяем что pytest-html установлен
    if hasattr(config, '_metadata'):
        # Добавляем информацию о проекте
        config._metadata['Проект'] = 'Gamification Tests'
        config._metadata['Версия'] = '1.0.0'
        config._metadata['Дата запуска'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Добавляем информацию об окружении
        config._metadata['Python'] = platform.python_version()
        config._metadata['Платформа'] = platform.platform()
        config._metadata['Процессор'] = platform.processor() or 'Unknown'
        
        # Добавляем информацию о тестируемом API
        config._metadata['API URL'] = 'http://localhost:8000'
        config._metadata['База данных'] = 'PostgreSQL'


def pytest_html_report_title(report):
    """
    Кастомизирует заголовок HTML отчета.
    """
    report.title = "Отчет о тестировании - Gamification System"


def pytest_html_results_table_header(cells):
    """
    Кастомизирует заголовки таблицы результатов в HTML отчете.
    Добавляет дополнительные колонки.
    """
    # Добавляем колонку с описанием теста
    cells.insert(2, '<th>Описание</th>')
    # Добавляем колонку с временем выполнения
    cells.insert(3, '<th class="sortable time" data-column-type="time">Время (сек)</th>')


def pytest_html_results_table_row(report, cells):
    """
    Кастомизирует строки таблицы результатов в HTML отчете.
    Добавляет данные в дополнительные колонки.
    """
    # Извлекаем docstring из теста для колонки "Описание"
    description = 'Нет описания'
    
    # Используем сохраненный docstring из pytest_runtest_makereport
    if hasattr(report, 'test_docstring') and report.test_docstring:
        # Берем первую строку docstring (обычно это краткое описание)
        docstring_lines = report.test_docstring.split('\n')
        # Берем первую непустую строку
        for line in docstring_lines:
            line = line.strip()
            if line and not line.startswith('"""') and not line.startswith("'''"):
                description = line
                break
        # Если не нашли, берем первую строку без кавычек
        if description == 'Нет описания' and docstring_lines:
            description = docstring_lines[0].strip().strip('"""').strip("'''").strip()
    
    # Добавляем описание (экранируем HTML для безопасности)
    import html
    description_escaped = html.escape(description) if description != 'Нет описания' else description
    cells.insert(2, f'<td>{description_escaped}</td>')
    
    # Добавляем время выполнения (округленное до 3 знаков)
    duration = getattr(report, 'duration', 0.0)
    cells.insert(3, f'<td class="col-time">{duration:.3f}</td>')


def pytest_html_results_summary(prefix, summary, postfix):
    """
    Добавляет дополнительную информацию в сводку результатов.
    """
    # Добавляем информацию перед таблицей результатов
    prefix.extend([
        '<div style="padding: 10px; background-color: #f0f0f0; border-radius: 5px; margin: 10px 0;">',
        '<h3>ℹ️ Информация о тестировании</h3>',
        '<p><strong>Система:</strong> Gamification Platform - система геймификации задач</p>',
        '<p><strong>Компоненты:</strong> API Backend (FastAPI), AI Analyzer (Groq), База данных (PostgreSQL)</p>',
        '<p><strong>Тестируемые модули:</strong> Chat API, Security, CRUD операции, AI Integration</p>',
        '</div>'
    ])


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Хук для добавления дополнительной информации к каждому тесту.
    Добавляет скриншоты, логи и другую полезную информацию при ошибках.
    Сохраняет docstring теста в report для использования в таблице результатов.
    """
    # Получаем результат выполнения теста
    outcome = yield
    report = outcome.get_result()
    
    # Сохраняем docstring теста в report для использования в pytest_html_results_table_row
    if hasattr(item, 'function') and item.function.__doc__:
        # Сохраняем docstring в report для последующего использования
        report.test_docstring = item.function.__doc__.strip()
    else:
        report.test_docstring = None
    
    # Добавляем дополнительную информацию только для HTML отчета
    extra = getattr(report, 'extra', [])
    
    if report.when == 'call':
        # Добавляем информацию о тесте
        if hasattr(item, 'function') and item.function.__doc__:
            # Добавляем полный docstring в дополнительную секцию
            # Используем правильный формат для pytest-html
            from pytest_html import extras
            extra.append(extras.html(f'<div><h4>Описание теста:</h4><pre>{item.function.__doc__}</pre></div>'))
        
        # При ошибке добавляем дополнительную отладочную информацию
        if report.failed:
            from pytest_html import extras
            extra.append(extras.html(f'<div style="color: red;"><strong>❌ Тест завершился с ошибкой в файле:</strong> {item.location[0]}</div>'))
            extra.append(extras.html(f'<div><strong>Расположение:</strong><br>Файл: <code>{item.location[0]}</code><br>Функция: <code>{item.location[2]}</code></div>'))
    
    report.extra = extra


# ============= Основные фикстуры =============

@pytest.fixture(scope="function")
def client():
    Base.metadata.create_all(bind=engine)

    with TestClient(app) as c:
        yield c

    with engine.connect() as conn:
        trans = conn.begin()
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(text(f"TRUNCATE TABLE {table.name} RESTART IDENTITY CASCADE"))
        trans.commit()


@pytest.fixture(autouse=True)
def mock_ai_analyzer():
    with patch("routes_post.analyze_task") as mock:
        mock.return_value = {"estimated_points": 10, "complexity": "medium", "suggested_tags": []}
        yield mock