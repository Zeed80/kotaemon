"""Система динамической адаптации промптов для GraphRAG на основе запроса пользователя и типа задачи."""

import logging
from typing import Any, Dict, Optional

from ktem.llms.manager import llms
from kotaemon.base.schema import AIMessage, HumanMessage, SystemMessage

logger = logging.getLogger(__name__)


class TaskType:
    """Типы задач для адаптации промптов."""

    ENTITY_EXTRACTION = "entity_extraction"
    RELATIONSHIP_EXTRACTION = "relationship_extraction"
    COMMUNITY_ANALYSIS = "community_analysis"
    TEXT_SUMMARIZATION = "text_summarization"
    QUESTION_ANSWERING = "question_answering"
    FACTUAL_QUERY = "factual_query"
    ANALYTICAL_QUERY = "analytical_query"
    COMPARISON_QUERY = "comparison_query"
    TEMPORAL_QUERY = "temporal_query"
    GENERAL = "general"


class PromptAdapter:
    """Адаптер промптов для динамической настройки на основе запроса пользователя."""

    def __init__(self, llm=None):
        """Инициализация адаптера промптов.

        Args:
            llm: LLM для анализа запросов (опционально, используется по умолчанию).
        """
        self.llm = llm or llms.get_default()
        self._task_type_cache: Dict[str, str] = {}

    def detect_task_type(self, query: str) -> str:
        """Определить тип задачи на основе запроса пользователя.

        Args:
            query: Запрос пользователя.

        Returns:
            Тип задачи из TaskType.
        """
        # Проверяем кэш
        if query in self._task_type_cache:
            return self._task_type_cache[query]

        query_lower = query.lower()

        # Простые эвристики для быстрого определения
        if any(word in query_lower for word in ["кто", "что", "где", "когда", "какой", "who", "what", "where", "when", "which"]):
            if any(word in query_lower for word in ["сравни", "разница", "отличие", "compare", "difference", "versus", "vs"]):
                task_type = TaskType.COMPARISON_QUERY
            elif any(word in query_lower for word in ["когда", "время", "период", "год", "месяц", "when", "time", "period", "year", "month"]):
                task_type = TaskType.TEMPORAL_QUERY
            elif any(word in query_lower for word in ["как", "почему", "зачем", "how", "why"]):
                task_type = TaskType.ANALYTICAL_QUERY
            else:
                task_type = TaskType.FACTUAL_QUERY
        elif any(word in query_lower for word in ["сущность", "объект", "entity", "object"]):
            task_type = TaskType.ENTITY_EXTRACTION
        elif any(word in query_lower for word in ["связь", "отношение", "relationship", "relation", "connection"]):
            task_type = TaskType.RELATIONSHIP_EXTRACTION
        elif any(word in query_lower for word in ["сообщество", "группа", "community", "group", "cluster"]):
            task_type = TaskType.COMMUNITY_ANALYSIS
        elif any(word in query_lower for word in ["суммар", "кратко", "summary", "summarize", "краткое"]):
            task_type = TaskType.TEXT_SUMMARIZATION
        else:
            # Используем LLM для более точного определения
            task_type = self._detect_task_type_with_llm(query)

        self._task_type_cache[query] = task_type
        return task_type

    def _detect_task_type_with_llm(self, query: str) -> str:
        """Использовать LLM для определения типа задачи.

        Args:
            query: Запрос пользователя.

        Returns:
            Тип задачи.
        """
        try:
            system_prompt = (
                "Определи тип задачи для следующего запроса пользователя. "
                "Выбери один из типов:\n"
                "- factual_query: простой фактологический вопрос (кто, что, где, когда)\n"
                "- analytical_query: аналитический вопрос (как, почему, зачем)\n"
                "- comparison_query: сравнение или сопоставление\n"
                "- temporal_query: вопрос о времени, периодах, хронологии\n"
                "- entity_extraction: извлечение сущностей\n"
                "- relationship_extraction: извлечение связей между сущностями\n"
                "- community_analysis: анализ сообществ или групп\n"
                "- text_summarization: суммаризация текста\n"
                "- question_answering: общий вопрос-ответ\n"
                "- general: общий запрос\n\n"
                "Ответь только одним словом - названием типа задачи."
            )

            messages = [
                SystemMessage(text=system_prompt),
                HumanMessage(text=f"Запрос: {query}\n\nТип задачи:"),
            ]

            response = self.llm(messages).text.strip().lower()

            # Маппинг ответов на типы задач
            task_mapping = {
                "factual": TaskType.FACTUAL_QUERY,
                "analytical": TaskType.ANALYTICAL_QUERY,
                "comparison": TaskType.COMPARISON_QUERY,
                "temporal": TaskType.TEMPORAL_QUERY,
                "entity": TaskType.ENTITY_EXTRACTION,
                "relationship": TaskType.RELATIONSHIP_EXTRACTION,
                "community": TaskType.COMMUNITY_ANALYSIS,
                "summarization": TaskType.TEXT_SUMMARIZATION,
                "question": TaskType.QUESTION_ANSWERING,
                "general": TaskType.GENERAL,
            }

            for key, task_type in task_mapping.items():
                if key in response:
                    return task_type

            return TaskType.GENERAL
        except Exception as e:
            logger.warning(f"Не удалось определить тип задачи через LLM: {e}")
            return TaskType.GENERAL

    def adapt_prompt(
        self,
        base_prompt: str,
        query: str,
        task_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Адаптировать базовый промпт на основе запроса и типа задачи.

        Args:
            base_prompt: Базовый промпт для адаптации.
            query: Запрос пользователя.
            task_type: Тип задачи (опционально, будет определен автоматически).
            context: Дополнительный контекст для адаптации (опционально).

        Returns:
            Адаптированный промпт.
        """
        if task_type is None:
            task_type = self.detect_task_type(query)

        adapted_prompt = base_prompt

        # Адаптация на основе типа задачи
        task_adaptations = {
            TaskType.FACTUAL_QUERY: (
                "Сфокусируйся на точных фактах и конкретной информации. "
                "Извлекай только проверяемые данные без интерпретаций."
            ),
            TaskType.ANALYTICAL_QUERY: (
                "Сфокусируйся на анализе и объяснении причинно-следственных связей. "
                "Предоставь глубокий анализ и интерпретацию информации."
            ),
            TaskType.COMPARISON_QUERY: (
                "Сфокусируйся на сравнении и сопоставлении. "
                "Выдели сходства и различия, используй структурированный формат."
            ),
            TaskType.TEMPORAL_QUERY: (
                "Сфокусируйся на временных аспектах и хронологии. "
                "Сохраняй временные метки и последовательность событий."
            ),
            TaskType.ENTITY_EXTRACTION: (
                "Сфокусируйся на извлечении всех значимых сущностей. "
                "Включи их типы, описания и характеристики."
            ),
            TaskType.RELATIONSHIP_EXTRACTION: (
                "Сфокусируйся на связях между сущностями. "
                "Извлекай все отношения с их типами и описаниями."
            ),
            TaskType.COMMUNITY_ANALYSIS: (
                "Сфокусируйся на сообществах и группах. "
                "Анализируй структуру сообществ и их характеристики."
            ),
            TaskType.TEXT_SUMMARIZATION: (
                "Сфокусируйся на создании краткого и информативного резюме. "
                "Сохраняй ключевые моменты и основную информацию."
            ),
        }

        if task_type in task_adaptations:
            adaptation = task_adaptations[task_type]
            # Добавляем адаптацию в начало промпта
            adapted_prompt = f"{adaptation}\n\n{adapted_prompt}"

        # Добавляем информацию о запросе пользователя, если это уместно
        if "{query}" not in adapted_prompt and "{question}" not in adapted_prompt:
            adapted_prompt = f"{adapted_prompt}\n\nКонтекст запроса пользователя: {query}"

        # Заменяем плейсхолдеры
        adapted_prompt = adapted_prompt.replace("{query}", query)
        adapted_prompt = adapted_prompt.replace("{question}", query)

        if context:
            for key, value in context.items():
                placeholder = f"{{{key}}}"
                if placeholder in adapted_prompt:
                    adapted_prompt = adapted_prompt.replace(placeholder, str(value))

        return adapted_prompt

    def adapt_prompts_dict(
        self,
        prompts_dict: Dict[str, str],
        query: str,
        task_type: Optional[str] = None,
    ) -> Dict[str, str]:
        """Адаптировать словарь промптов.

        Args:
            prompts_dict: Словарь промптов для адаптации.
            query: Запрос пользователя.
            task_type: Тип задачи (опционально).

        Returns:
            Словарь адаптированных промптов.
        """
        if task_type is None:
            task_type = self.detect_task_type(query)

        adapted_prompts = {}
        for prompt_name, prompt_content in prompts_dict.items():
            adapted_prompts[prompt_name] = self.adapt_prompt(
                prompt_content, query, task_type
            )

        return adapted_prompts


# Глобальный экземпляр адаптера
_prompt_adapter: Optional[PromptAdapter] = None


def get_prompt_adapter() -> PromptAdapter:
    """Получить глобальный экземпляр адаптера промптов."""
    global _prompt_adapter
    if _prompt_adapter is None:
        _prompt_adapter = PromptAdapter()
    return _prompt_adapter
