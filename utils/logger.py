"""
Настройка логирования для системы
"""

import os
import logging
import logging.handlers
from datetime import datetime
from typing import Optional, Dict, Any

def setup_logging(
    log_level: str = "INFO",
    log_dir: str = "logs",
    app_name: str = "ai_assistant",
    max_log_size: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5
) -> None:
    """Настраивает систему логирования"""
    
    # Создаем директорию для логов
    os.makedirs(log_dir, exist_ok=True)
    
    # Определяем уровень логирования
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Настраиваем корневой логгер
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[]
    )
    
    # Очищаем существующие обработчики
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Создаем форматтер
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )
    
    # Обработчик для консоли
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Обработчик для файла (общий лог)
    general_log_file = os.path.join(log_dir, f"{app_name}.log")
    general_handler = logging.handlers.RotatingFileHandler(
        general_log_file,
        maxBytes=max_log_size,
        backupCount=backup_count,
        encoding='utf-8'
    )
    general_handler.setLevel(level)
    general_handler.setFormatter(formatter)
    root_logger.addHandler(general_handler)
    
    # Обработчик для ошибок
    error_log_file = os.path.join(log_dir, f"{app_name}_errors.log")
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_file,
        maxBytes=max_log_size,
        backupCount=backup_count,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)
    
    # Обработчик для отладочной информации
    debug_log_file = os.path.join(log_dir, f"{app_name}_debug.log")
    debug_handler = logging.handlers.RotatingFileHandler(
        debug_log_file,
        maxBytes=max_log_size,
        backupCount=backup_count,
        encoding='utf-8'
    )
    debug_handler.setLevel(logging.DEBUG)
    debug_handler.setFormatter(formatter)
    root_logger.addHandler(debug_handler)
    
    # Устанавливаем уровень для корневого логгера
    root_logger.setLevel(level)
    
    # Логируем информацию о настройке
    root_logger.info(f"Логирование настроено: уровень={log_level}, директория={log_dir}")
    root_logger.info(f"Файлы логов: {general_log_file}, {error_log_file}, {debug_log_file}")

def get_logger(name: str) -> logging.Logger:
    """Получает логгер с указанным именем"""
    return logging.getLogger(name)

def log_function_call(func_name: str, args: tuple = None, kwargs: dict = None, 
                     logger: Optional[logging.Logger] = None) -> None:
    """Логирует вызов функции"""
    if logger is None:
        logger = get_logger(__name__)
    
    args_str = str(args) if args else "()"
    kwargs_str = str(kwargs) if kwargs else "{}"
    
    logger.debug(f"Вызов функции: {func_name}{args_str}, kwargs={kwargs_str}")

def log_function_result(func_name: str, result: Any, logger: Optional[logging.Logger] = None) -> None:
    """Логирует результат выполнения функции"""
    if logger is None:
        logger = get_logger(__name__)
    
    result_str = str(result)[:100] + "..." if len(str(result)) > 100 else str(result)
    logger.debug(f"Результат функции {func_name}: {result_str}")

def log_function_error(func_name: str, error: Exception, logger: Optional[logging.Logger] = None) -> None:
    """Логирует ошибку выполнения функции"""
    if logger is None:
        logger = get_logger(__name__)
    
    logger.error(f"Ошибка в функции {func_name}: {error}", exc_info=True)

def log_performance(func_name: str, execution_time: float, logger: Optional[logging.Logger] = None) -> None:
    """Логирует время выполнения функции"""
    if logger is None:
        logger = get_logger(__name__)
    
    if execution_time > 1.0:  # Логируем только медленные функции
        logger.warning(f"Медленное выполнение функции {func_name}: {execution_time:.2f} сек")
    else:
        logger.debug(f"Время выполнения функции {func_name}: {execution_time:.3f} сек")

def log_user_action(user_id: str, action: str, details: Dict[str, Any] = None, 
                   logger: Optional[logging.Logger] = None) -> None:
    """Логирует действия пользователя"""
    if logger is None:
        logger = get_logger(__name__)
    
    details_str = f" - {details}" if details else ""
    logger.info(f"Пользователь {user_id}: {action}{details_str}")

def log_system_event(event: str, details: Dict[str, Any] = None, 
                    logger: Optional[logging.Logger] = None) -> None:
    """Логирует системные события"""
    if logger is None:
        logger = get_logger(__name__)
    
    details_str = f" - {details}" if details else ""
    logger.info(f"Системное событие: {event}{details_str}")

def log_security_event(event: str, user_id: str = None, ip_address: str = None, 
                      details: Dict[str, Any] = None, logger: Optional[logging.Logger] = None) -> None:
    """Логирует события безопасности"""
    if logger is None:
        logger = get_logger(__name__)
    
    user_info = f" пользователь {user_id}" if user_id else ""
    ip_info = f" IP {ip_address}" if ip_address else ""
    details_str = f" - {details}" if details else ""
    
    logger.warning(f"Событие безопасности: {event}{user_info}{ip_info}{details_str}")

def log_database_operation(operation: str, table: str, record_id: str = None, 
                          details: Dict[str, Any] = None, logger: Optional[logging.Logger] = None) -> None:
    """Логирует операции с базой данных"""
    if logger is None:
        logger = get_logger(__name__)
    
    record_info = f" запись {record_id}" if record_id else ""
    details_str = f" - {details}" if details else ""
    
    logger.debug(f"Операция БД: {operation} в таблице {table}{record_info}{details_str}")

def log_api_request(method: str, endpoint: str, user_id: str = None, 
                   status_code: int = None, response_time: float = None,
                   logger: Optional[logging.Logger] = None) -> None:
    """Логирует API запросы"""
    if logger is None:
        logger = get_logger(__name__)
    
    user_info = f" пользователь {user_id}" if user_id else ""
    status_info = f" статус {status_code}" if status_code else ""
    time_info = f" время {response_time:.3f}с" if response_time else ""
    
    logger.info(f"API запрос: {method} {endpoint}{user_info} - {status_info} {time_info}")

def get_log_stats(log_dir: str = "logs") -> Dict[str, Any]:
    """Получает статистику логов"""
    stats = {
        'total_files': 0,
        'total_size_mb': 0,
        'files': []
    }
    
    try:
        for filename in os.listdir(log_dir):
            if filename.endswith('.log'):
                file_path = os.path.join(log_dir, filename)
                file_size = os.path.getsize(file_path)
                file_stats = os.stat(file_path)
                
                stats['total_files'] += 1
                stats['total_size_mb'] += file_size / (1024 * 1024)
                
                stats['files'].append({
                    'name': filename,
                    'size_mb': round(file_size / (1024 * 1024), 2),
                    'modified': datetime.fromtimestamp(file_stats.st_mtime).isoformat()
                })
        
        stats['total_size_mb'] = round(stats['total_size_mb'], 2)
        
    except Exception as e:
        stats['error'] = str(e)
    
    return stats

def cleanup_old_logs(log_dir: str = "logs", max_age_days: int = 30) -> int:
    """Очищает старые логи"""
    cleaned_count = 0
    cutoff_time = datetime.now().timestamp() - (max_age_days * 24 * 3600)
    
    try:
        for filename in os.listdir(log_dir):
            if filename.endswith('.log'):
                file_path = os.path.join(log_dir, filename)
                file_stats = os.stat(file_path)
                
                if file_stats.st_mtime < cutoff_time:
                    os.remove(file_path)
                    cleaned_count += 1
                    
    except Exception as e:
        logger = get_logger(__name__)
        logger.error(f"Ошибка очистки старых логов: {e}")
    
    return cleaned_count
