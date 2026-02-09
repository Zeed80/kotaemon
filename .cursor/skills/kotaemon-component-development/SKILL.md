---
name: kotaemon-component-development
description: Пошаговое создание компонентов kotaemon. Использовать при создании новых компонентов, пайплайнов, LLM/embeddings/retrievers.
---

# Kotaemon Component Development

## Checklist

- [ ] Класс наследует `kotaemon.base.BaseComponent`
- [ ] Параметры объявлены с `Param` (или как атрибуты класса)
- [ ] Подкомпоненты объявлены с типом `BaseComponent` (Node)
- [ ] Реализован метод `run(*args, **kwargs)` с корректной сигнатурой возврата

## Шаблон компонента

```python
from kotaemon.base import BaseComponent, Node, Param, Document


class MyPipeline(BaseComponent):
    param1: str = "default"
    param2: int = 10

    node1: BaseComponent  # подкомпонент
    node2: BaseComponent

    def run(self, input_data: str | Document) -> Document | list[Document]:
        # обработка
        result = self.node1(input_data)
        return self.node2(result)
```

## Reasoning / Indexing

Для нового reasoning pipeline:
1. Создать класс в `libs/ktem/ktem/reasoning/`
2. Зарегистрировать в flowsettings: `KH_REASONINGS.append("ktem.reasoning.mymodule.MyPipeline")`

Для нового index type:
1. Создать класс в `libs/ktem/ktem/index/file/`
2. Добавить в flowsettings: `KH_INDEX_TYPES.append("ktem.index.file.mymodule.MyIndex")`

## Дополнительно

- Подробное руководство: [docs/development/create-a-component.md](../../../docs/development/create-a-component.md)
- Пример FancyPipeline в документации
