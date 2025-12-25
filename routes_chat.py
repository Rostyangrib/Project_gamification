import re  # Импорт модуля для работы с регулярными выражениями
from typing import Optional, List  # Импорт типов для аннотаций: Optional (опциональное значение) и List (список)
from datetime import datetime  # Импорт класса datetime для работы с датами и временем
from fastapi import APIRouter, Depends, HTTPException  # Импорт компонентов FastAPI: роутер, зависимости и исключения
from sqlalchemy.orm import Session  # Импорт сессии SQLAlchemy для работы с базой данных
from pydantic import BaseModel  # Импорт базового класса для создания моделей данных с валидацией
import requests  # Импорт библиотеки для HTTP-запросов
from ml.ai_analyzer import analyze_task_with_commands, analyze_task, YandexRateLimitError, YandexAPIError  # Импорт функций анализа задач и исключений AI-сервиса
from db import get_db  # Импорт функции для получения сессии базы данных
from database import User, Task, TaskStatus, Tag, TaskTag, Competition  # Импорт моделей базы данных: пользователь, задача, статус, тег, связь задачи с тегом, соревнование
from schemas import TaskResponse  # Импорт схемы ответа для задачи
from dependencies import get_current_user  # Импорт функции для получения текущего авторизованного пользователя

router = APIRouter()  # Создание роутера для группировки эндпоинтов

class ChatMessage(BaseModel):  # Определение модели данных для входящего сообщения чата
    message: str  # Текст сообщения от пользователя
    user_ids: Optional[List[int]] = None  # Опциональный список ID пользователей, для которых создается задача (если None, то для текущего пользователя)


class ChatResponse(BaseModel):  # Определение модели данных для ответа чата
    reply: str  # Текст ответа от AI или системы
    task_created: TaskResponse | None = None  # Опциональный объект созданной задачи (если задача была создана)

@router.post("/api/chat", response_model=ChatResponse)  # Регистрация POST-эндпоинта /api/chat с указанием модели ответа
@router.post("/chat", response_model=ChatResponse)  # Регистрация альтернативного POST-эндпоинта /chat с указанием модели ответа
def chat_with_ai(  # Определение функции обработки запроса на создание задачи через чат
    chat: ChatMessage,  # Параметр: входящее сообщение чата (валидируется через Pydantic)
    current_user: dict = Depends(get_current_user),  # Параметр: текущий авторизованный пользователь (получается через зависимость)
    db: Session = Depends(get_db)  # Параметр: сессия базы данных (получается через зависимость)
):
    """
    Принимает естественный язык и создаёт задачу.
    Пример: "Создай задачу 'Купить фрукты' на 12.12.2025, статус В работе, тег срочно"
    """
    statuses = [{"code": s.code, "name": s.name} for s in db.query(TaskStatus).all()]  # Получение всех статусов задач из БД и преобразование в список словарей с кодом и названием
    tags = [t.name for t in db.query(Tag).all()]  # Получение всех тегов из БД и преобразование в список названий

    try:  # Начало блока обработки исключений при обращении к AI
        ai_response = analyze_task_with_commands(  # Вызов функции анализа задачи с командами, которая парсит естественный язык
            user_message=chat.message,  # Передача текста сообщения пользователя
            available_statuses=statuses,  # Передача списка доступных статусов задач
            available_tags=tags  # Передача списка доступных тегов
        )
    except YandexRateLimitError as e:  # Обработка исключения превышения лимита запросов к Yandex API
        # Специальная обработка ошибки rate limit - пробрасываем HTTP 429
        # Это позволит тестам фиксировать ошибку
        raise HTTPException(  # Выброс HTTP-исключения с кодом 429 (Too Many Requests)
            status_code=429,  # Установка HTTP-кода статуса 429
            detail="Слишком много запросов к AI. Пожалуйста, подождите несколько секунд и попробуйте снова."  # Сообщение об ошибке для пользователя
        )
    except YandexAPIError as e:  # Обработка других ошибок Yandex Cloud API
        # Обработка других ошибок Yandex Cloud API
        raise HTTPException(  # Выброс HTTP-исключения с кодом 503 (Service Unavailable)
            status_code=503,  # Установка HTTP-кода статуса 503
            detail=f"Ошибка при обращении к AI сервису: {str(e)}"  # Сообщение об ошибке с деталями исключения
        )
    except requests.exceptions.HTTPError as e:  # Обработка HTTP-ошибок из библиотеки requests (на случай если они не были перехвачены)
        # Обработка других HTTP ошибок (на случай если они не были перехвачены)
        if e.response.status_code == 429:  # Проверка, является ли ошибка превышением лимита запросов
            raise HTTPException(  # Выброс HTTP-исключения с кодом 429
                status_code=429,  # Установка HTTP-кода статуса 429
                detail="Слишком много запросов к AI. Пожалуйста, подождите несколько секунд и попробуйте снова."  # Сообщение об ошибке
            )
        raise HTTPException(  # Выброс HTTP-исключения с кодом 500 для других HTTP-ошибок
            status_code=500,  # Установка HTTP-кода статуса 500 (Internal Server Error)
            detail=f"Ошибка при обращении к AI сервису: {str(e)}"  # Сообщение об ошибке с деталями
        )
    except Exception as e:  # Обработка всех остальных неожиданных исключений
        # Обработка всех остальных ошибок
        raise HTTPException(  # Выброс HTTP-исключения с кодом 500
            status_code=500,  # Установка HTTP-кода статуса 500
            detail=f"Внутренняя ошибка сервера: {str(e)}"  # Сообщение об общей внутренней ошибке с деталями
        )

    if not ai_response.get("commands"):  # Проверка наличия команд в ответе AI (если команд нет, значит AI просто ответил, но не создал задачу)
        return ChatResponse(reply=ai_response["reply"])  # Возврат ответа только с текстом от AI, без создания задачи

    cmd = ai_response["commands"][0]  # Извлечение первой команды из списка команд (обычно команда создания задачи)
    if cmd.get("action") != "create_task":  # Проверка, что действие команды - создание задачи
        return ChatResponse(reply="Я пока умею только создавать задачи.")  # Возврат сообщения, если команда не для создания задачи

    task_data = cmd.get("task_data", {})  # Извлечение данных задачи из команды (словарь с полями задачи)
    title = str(task_data.get("title", "")).strip()  # Получение названия задачи, преобразование в строку и удаление пробелов по краям
    if not title:  # Проверка, что название задачи не пустое
        return ChatResponse(reply="Не удалось определить название задачи.")  # Возврат ошибки, если название не определено

    status_code = str(task_data.get("status_code", "todo")).strip()  # Получение кода статуса задачи (по умолчанию "todo"), преобразование в строку и удаление пробелов
    status_obj = db.query(TaskStatus).filter(TaskStatus.code == status_code).first()  # Поиск объекта статуса в БД по коду
    if not status_obj:  # Проверка, найден ли статус в БД
        fallback_status = db.query(TaskStatus).first()  # Получение первого доступного статуса из БД как запасной вариант
        if fallback_status:  # Проверка, есть ли хотя бы один статус в БД
            status_obj = fallback_status  # Использование первого найденного статуса
        else:  # Если в БД нет ни одного статуса
            status_obj = TaskStatus(code="todo", name="К выполнению")  # Создание нового статуса по умолчанию
            db.add(status_obj)  # Добавление статуса в сессию БД
            db.commit()  # Сохранение изменений в БД
            db.refresh(status_obj)  # Обновление объекта статуса из БД (получение ID)

    due_date = task_data.get("due_date")  # Получение даты выполнения задачи из данных команды
    
    # Преобразование строки в datetime, если необходимо
    if due_date and isinstance(due_date, str):  # Проверка, является ли due_date строкой
        try:  # Начало блока обработки ошибок при парсинге даты
            due_date = datetime.fromisoformat(due_date.replace('Z', '+00:00'))  # Преобразование строки ISO формата в datetime объект
        except (ValueError, AttributeError):  # Обработка ошибок парсинга даты
            try:  # Попытка парсинга в другом формате
                due_date = datetime.strptime(due_date, "%Y-%m-%dT%H:%M:%S")  # Парсинг даты в формате "ГГГГ-ММ-ДДTЧЧ:ММ:СС"
            except ValueError:  # Если и этот формат не подошел
                due_date = None  # Установка due_date в None при ошибке парсинга
    
    if due_date and hasattr(due_date, 'tzinfo') and due_date.tzinfo is not None:  # Проверка наличия временной зоны у даты
        due_date = due_date.replace(tzinfo=None)  # Удаление информации о временной зоне из даты (приведение к naive datetime)

    if not due_date:  # Проверка наличия даты выполнения задачи
        return ChatResponse(  # Возврат ответа с ошибкой, если дата не указана
            reply=(
                ai_response.get("reply", "")  # Получение ответа от AI, если он был сгенерирован
                + " В запросе не указана конкретная дата выполнения задачи. "  # Добавление сообщения об отсутствии даты
                  "Пожалуйста, добавьте дату в формате ДД.ММ.ГГГГ и повторите запрос."  # Добавление инструкции по формату даты
            ).strip()  # Удаление лишних пробелов в начале и конце строки
        )

    description = str(task_data.get("description", "")).strip()  # Получение описания задачи, преобразование в строку и удаление пробелов по краям

    normalized_title = re.sub(r"\s+", " ", title.lower())  # Нормализация названия: приведение к нижнему регистру и замена множественных пробелов одним
    normalized_desc = re.sub(r"\s+", " ", description.lower())  # Нормализация описания: приведение к нижнему регистру и замена множественных пробелов одним

    banned_fragments = [  # Определение списка запрещенных фрагментов текста
        "покур", "раскур", "курить", "курев", "сигарет", "кальян",  # Слова, связанные с курением
    ]
    if any(frag in normalized_title or frag in normalized_desc for frag in banned_fragments):  # Проверка наличия запрещенных фрагментов в названии или описании
        return ChatResponse(  # Возврат ответа с ошибкой, если найдены запрещенные слова
            reply=(
                ai_response.get("reply", "")  # Получение ответа от AI
                + " Я не могу создавать задачи, связанные с курением или подобными действиями. "  # Добавление сообщения о запрете
                  "Пожалуйста, переформулируйте запрос в безопасном и рабочем контексте."  # Добавление инструкции по переформулировке
            ).strip()  # Удаление лишних пробелов
        )

    if not description:  # Проверка наличия описания задачи (не пустое ли оно)
        return ChatResponse(  # Возврат ответа с ошибкой, если описание отсутствует
            reply=(
                ai_response.get("reply", "")  # Получение ответа от AI
                + " Описание задачи отсутствует или получилось пустым. "  # Добавление сообщения об отсутствии описания
                  "Пожалуйста, добавьте краткое, понятное описание: что именно нужно сделать и к какому результату прийти."  # Добавление инструкции по заполнению описания
            ).strip()  # Удаление лишних пробелов
        )
    
    

    if normalized_desc == normalized_title and len(normalized_desc.split()) <= 3:  # Проверка, что описание не отличается от названия и содержит не более 3 слов
        return ChatResponse(  # Возврат ответа с ошибкой, если описание слишком короткое и повторяет заголовок
            reply=(
                ai_response.get("reply", "")  # Получение ответа от AI
                + " Описание задачи слишком короткое и повторяет заголовок. "  # Добавление сообщения о недостаточности описания
                  "Пожалуйста, уточните, что именно нужно сделать, где и к какому результату прийти."  # Добавление инструкции по уточнению описания
            ).strip()  # Удаление лишних пробелов
        )

    # Используем estimated_points из первого AI запроса, чтобы избежать дублирования вызовов
    estimated_points = task_data.get("estimated_points", 50)  # Получение оценки сложности задачи из данных команды (по умолчанию 50 баллов)
    
    # Если estimated_points не был установлен в первом запросе, вызываем analyze_task
    # Это может произойти только если analyze_task_with_commands не смог определить сложность
    if estimated_points == 50 and "estimated_points" not in task_data:  # Проверка, что оценка не была установлена (значение по умолчанию и отсутствие в данных)
        try:  # Начало блока обработки исключений при анализе задачи
            ai_analysis = analyze_task(title, description)  # Вызов функции анализа задачи для определения сложности и оценки
            # Проверяем, является ли задача бессмысленной
            if ai_analysis.get("estimated_points") is None or ai_analysis.get("is_meaningless"):  # Проверка, что задача не бессмысленна и оценка определена
                return ChatResponse(  # Возврат ответа с ошибкой, если задача бессмысленна
                    reply=f"Задача бессмысленна или неконкретна: {ai_analysis.get('explanation', 'Не удалось оценить задачу')}"  # Сообщение с объяснением от AI
                )
            estimated_points = ai_analysis["estimated_points"]  # Сохранение оценки сложности из анализа
        except (YandexRateLimitError, YandexAPIError) as e:  # Обработка ошибок API Yandex при анализе
            # Если произошла ошибка API при оценке сложности, пробрасываем её дальше
            # Это позволит тестам фиксировать ошибку
            raise  # Повторный выброс исключения для обработки на верхнем уровне
    else:  # Если оценка уже была получена из первого запроса
        # Создаем минимальный ai_analysis для совместимости
        ai_analysis = {  # Создание словаря с метаданными анализа для совместимости с остальным кодом
            "estimated_points": estimated_points,  # Сохранение оценки сложности
            "explanation": "Оценка получена из первичного анализа",  # Текст объяснения
            "model_used": "cached",  # Указание, что использована кэшированная оценка
            "confidence": 0.8  # Уровень уверенности в оценке
        }

    user_ids_to_create = chat.user_ids if chat.user_ids else [current_user["user"].id]  # Определение списка ID пользователей: если указаны в запросе - используем их, иначе - текущий пользователь
    
    users = db.query(User).filter(User.id.in_(user_ids_to_create)).all()  # Получение всех пользователей из БД по списку ID
    if len(users) != len(user_ids_to_create):  # Проверка, что все указанные пользователи найдены в БД
        return ChatResponse(reply="Один или несколько указанных пользователей не найдены.")  # Возврат ошибки, если не все пользователи найдены

    # Проверка, что дата выполнения задачи находится в рамках дедлайна соревнования
    for user in users:  # Перебираем всех пользователей, для которых создается задача
        if user.cur_comp is not None:  # Проверяем, участвует ли пользователь в каком-либо соревновании
            competition = db.query(Competition).filter(Competition.id == user.cur_comp).first()  # Получаем объект соревнования из базы данных по его ID
            if competition:  # Если соревнование существует в базе данных
                if due_date < competition.start_date or due_date > competition.end_date:  # Проверяем, что дата выполнения задачи находится в пределах периода соревнования (между началом и концом)
                    return ChatResponse(  # Возвращаем ответ с ошибкой, если дата выходит за рамки соревнования
                        reply=(
                            ai_response.get("reply", "")  # Берем ответ от AI, если он был сгенерирован
                            + f" Дата выполнения задачи ({due_date.strftime('%d.%m.%Y') if isinstance(due_date, datetime) else str(due_date)}) выходит за рамки "  # Форматируем дату задачи в читаемый формат (проверяя тип) и добавляем к сообщению
                              f"соревнования «{competition.title}» (с {competition.start_date.strftime('%d.%m.%Y')} "  # Добавляем название соревнования и дату начала в читаемом формате
                              f"по {competition.end_date.strftime('%d.%m.%Y')}). "  # Добавляем дату окончания соревнования в читаемом формате
                              "Пожалуйста, укажите дату в пределах периода соревнования."  # Добавляем инструкцию для пользователя
                        ).strip()  # Убираем лишние пробелы в начале и конце строки
                    )

    created_tasks = []  # Инициализация списка созданных задач
    attached_tags = []  # Инициализация списка прикрепленных тегов
    
    for user_id in user_ids_to_create:  # Перебор всех пользователей, для которых создается задача
        new_task = Task(  # Создание нового объекта задачи
            user_id=user_id,  # Установка ID пользователя-владельца задачи
            status_id=status_obj.id,  # Установка ID статуса задачи
            title=title,  # Установка названия задачи
            description=description,  # Установка описания задачи
            estimated_points=estimated_points,  # Установка оценки сложности задачи
            ai_analysis_metadata=ai_analysis,  # Установка метаданных анализа AI
            due_date=due_date,  # Установка даты выполнения задачи
            awarded_points=0  # Установка начисленных баллов (по умолчанию 0)
        )
        db.add(new_task)  # Добавление задачи в сессию БД
        db.flush()  # Принудительная отправка SQL-запроса в БД для получения ID задачи (без коммита)
        
        for tag_name in task_data.get("tags", []):  # Перебор всех тегов из данных команды
            if not isinstance(tag_name, str) or not tag_name.strip():  # Проверка, что тег - непустая строка
                continue  # Пропуск некорректных тегов
            tag_name = tag_name.strip()  # Удаление пробелов по краям названия тега
            tag = db.query(Tag).filter(Tag.name == tag_name).first()  # Поиск тега в БД по названию
            if not tag:  # Проверка, существует ли тег в БД
                tag = Tag(name=tag_name)  # Создание нового тега, если его нет
                db.add(tag)  # Добавление тега в сессию БД
                db.flush()  # Принудительная отправка SQL-запроса для получения ID тега
            existing = db.query(TaskTag).filter(  # Поиск существующей связи задачи с тегом
                TaskTag.task_id == new_task.id,  # Фильтр по ID задачи
                TaskTag.tag_id == tag.id  # Фильтр по ID тега
            ).first()
            if not existing:  # Проверка, что связь еще не существует
                db.add(TaskTag(task_id=new_task.id, tag_id=tag.id))  # Создание связи задачи с тегом
                if tag_name not in attached_tags:  # Проверка, что тег еще не добавлен в список
                    attached_tags.append(tag_name)  # Добавление названия тега в список для отчета
        
        created_tasks.append(new_task)  # Добавление созданной задачи в список

    db.commit()  # Сохранение всех изменений в БД (задачи, теги, связи)
    
    for task in created_tasks:  # Перебор всех созданных задач
        db.refresh(task)  # Обновление объектов задач из БД (получение актуальных данных, включая ID)

    reply = f" Задача «{title}» создана"  # Начало формирования ответа с названием задачи
    if len(created_tasks) > 1:  # Проверка, создана ли задача для нескольких пользователей
        reply += f" для {len(created_tasks)} пользователей"  # Добавление информации о количестве пользователей
    if due_date:  # Проверка наличия даты выполнения
        reply += f" Срок: {due_date}."  # Добавление информации о сроке выполнения
    if attached_tags:  # Проверка наличия прикрепленных тегов
        reply += f" Теги: {', '.join(attached_tags)}."  # Добавление списка тегов через запятую
    reply += f" Статус: {status_obj.name}."  # Добавление информации о статусе задачи

    first_task = created_tasks[0] if created_tasks else None  # Получение первой созданной задачи (или None, если задач нет)

    return ChatResponse(  # Возврат ответа с результатом создания задачи
        reply=ai_response["reply"] + " " + reply,  # Объединение ответа AI с информацией о созданной задаче
        task_created=TaskResponse.from_orm(first_task) if first_task else None  # Преобразование первой задачи в схему ответа (или None)
    )
