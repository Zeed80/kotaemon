"""Monkey patch для исправления несовместимости httplib2 с pyparsing 3.x.

httplib2 использует устаревший API pyparsing (DelimitedList вместо delimitedList).
Этот патч исправляет проблему при импорте httplib2.

Проблема: httplib2.auth использует pp.DelimitedList, который был переименован
в pp.delimitedList в pyparsing 3.x. Хотя httplib2 0.31.2 заявляет совместимость
с pyparsing 3.x, в коде всё ещё используется старый API.
"""


def patch_httplib2_pyparsing():
    """Применить патч для совместимости httplib2 с pyparsing 3.x.
    
    Патч должен быть применен ДО импорта httplib2 или любых модулей,
    которые импортируют httplib2 (например, google.generativeai).
    """
    try:
        import pyparsing as pp

        # В pyparsing 3.x DelimitedList был переименован в delimitedList
        # Создаем алиас для обратной совместимости с httplib2
        if hasattr(pp, "delimitedList") and not hasattr(pp, "DelimitedList"):
            pp.DelimitedList = pp.delimitedList

    except ImportError:
        # pyparsing не установлен, патч не нужен
        pass
    except Exception:
        # Игнорируем ошибки при патчинге
        pass


# Применяем патч при импорте модуля (до импорта httplib2)
patch_httplib2_pyparsing()
