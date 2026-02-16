from sqlalchemy import select
from sqlalchemy.orm import Session
from theflow.settings import settings as flowsettings
from theflow.utils.modules import deserialize

from kotaemon.rerankings.base import BaseReranking

from .db import RerankingTable, engine


class RerankingManager:
    """Represent a pool of rerankings models"""

    def __init__(self):
        self._models: dict[str, BaseReranking] = {}
        self._info: dict[str, dict] = {}
        self._default: str = ""
        self._vendors: list[type] = []

        # populate the pool if empty
        if hasattr(flowsettings, "KH_RERANKINGS"):
            with Session(engine) as sess:
                count = sess.query(RerankingTable).count()
            if not count:
                for name, model in flowsettings.KH_RERANKINGS.items():
                    self.add(
                        name=name,
                        spec=model["spec"],
                        default=model.get("default", False),
                    )

        self.load()
        self.load_vendors()

    def load(self):
        """Load the model pool from database"""
        from ktem.utils.secret_storage import process_dict_for_load

        self._models, self._info, self._default = {}, {}, ""
        with Session(engine) as sess:
            stmt = select(RerankingTable)
            items = sess.execute(stmt)

            for (item,) in items:
                try:
                    spec = dict(item.spec or {})
                    process_dict_for_load(spec)
                    self._models[item.name] = deserialize(spec, safe=False)
                    self._info[item.name] = {
                        "name": item.name,
                        "spec": spec,
                        "default": item.default,
                    }
                    if item.default:
                        self._default = item.name
                except Exception as e:
                    import logging

                    logging.getLogger(__name__).warning(
                        "Skipping reranking %r due to load error: %s", item.name, e
                    )

    def reload_one(self, name: str) -> None:
        """Перезагрузить только одну модель из БД (без полного load всех реранкеров)."""
        from ktem.utils.secret_storage import process_dict_for_load

        with Session(engine) as sess:
            item = sess.query(RerankingTable).filter_by(name=name).first()
            if not item:
                if name in self._models:
                    del self._models[name]
                    del self._info[name]
                    if self._default == name:
                        self._default = next(iter(self._models), "") or ""
                return
            try:
                spec = dict(item.spec or {})
                process_dict_for_load(spec)
                self._models[name] = deserialize(spec, safe=False)
                self._info[name] = {
                    "name": item.name,
                    "spec": spec,
                    "default": item.default,
                }
                if item.default:
                    self._default = name
            except Exception as e:
                import logging

                logging.getLogger(__name__).warning(
                    "Skipping reranking %r due to reload error: %s", name, e
                )

    def load_vendors(self):
        from kotaemon.rerankings import (
            CohereReranking,
            OllamaReranking,
            TeiFastReranking,
            VoyageAIReranking,
        )

        self._vendors = [
            TeiFastReranking,
            CohereReranking,
            VoyageAIReranking,
            OllamaReranking,
        ]

    def __getitem__(self, key: str) -> BaseReranking:
        """Get model by name"""
        return self._models[key]

    def __contains__(self, key: str) -> bool:
        """Check if model exists"""
        return key in self._models

    def get(
        self, key: str, default: BaseReranking | None = None
    ) -> BaseReranking | None:
        """Get model by name with default value"""
        return self._models.get(key, default)

    def settings(self) -> dict:
        """Present model pools option for gradio"""
        return {
            "label": "Reranking",
            "choices": list(self._models.keys()),
            "value": self.get_default_name(),
        }

    def options(self) -> dict:
        """Present a dict of models"""
        return self._models

    def get_random_name(self) -> str:
        """Get the name of random model

        Returns:
            str: random model name in the pool
        """
        import random

        if not self._models:
            raise ValueError("No models is pool")

        return random.choice(list(self._models.keys()))

    def get_default_name(self) -> str:
        """Get the name of default model

        In case there is no default model, choose random model from pool. In
        case there are multiple default models, choose random from them.

        Returns:
            str: model name
        """
        if not self._models:
            raise ValueError("No models in pool")

        if not self._default:
            return self.get_random_name()

        return self._default

    def get_random(self) -> BaseReranking:
        """Get random model"""
        return self._models[self.get_random_name()]

    def get_default(self) -> BaseReranking:
        """Get default model

        In case there is no default model, choose random model from pool. In
        case there are multiple default models, choose random from them.

        Returns:
            BaseReranking: model
        """
        return self._models[self.get_default_name()]

    def info(self) -> dict:
        """List all models"""
        return self._info

    def add(self, name: str, spec: dict, default: bool):
        from ktem.utils.secret_storage import process_dict_for_save

        if not name:
            raise ValueError("Name must not be empty")

        spec_to_store = dict(spec)
        process_dict_for_save(spec_to_store)

        try:
            with Session(engine) as sess:
                if default:
                    # turn all models to non-default
                    sess.query(RerankingTable).update({"default": False})
                    sess.commit()

                item = RerankingTable(name=name, spec=spec_to_store, default=default)
                sess.add(item)
                sess.commit()
        except Exception as e:
            raise ValueError(f"Failed to add model {name}: {e}")

        self.reload_one(name)
        if default:
            self._default = name
            for k in self._info:
                if k != name:
                    self._info[k]["default"] = False

    def delete(self, name: str):
        """Delete a model from the pool"""
        try:
            with Session(engine) as sess:
                item = sess.query(RerankingTable).filter_by(name=name).first()
                sess.delete(item)
                sess.commit()
        except Exception as e:
            raise ValueError(f"Failed to delete model {name}: {e}")

        self.reload_one(name)

    def update(self, name: str, spec: dict, default: bool):
        """Update a model in the pool"""
        from ktem.utils.secret_storage import process_dict_for_save

        if not name:
            raise ValueError("Name must not be empty")

        spec_to_store = dict(spec)
        process_dict_for_save(spec_to_store)

        try:
            with Session(engine) as sess:
                if default:
                    # turn all models to non-default
                    sess.query(RerankingTable).update({"default": False})
                    sess.commit()

                item = sess.query(RerankingTable).filter_by(name=name).first()
                if not item:
                    raise ValueError(f"Model {name} not found")
                item.spec = spec_to_store
                item.default = default
                sess.commit()
        except Exception as e:
            raise ValueError(f"Failed to update model {name}: {e}")

        self.reload_one(name)
        if default:
            self._default = name
            for k in self._info:
                if k != name:
                    self._info[k]["default"] = False
        elif self._default == name:
            # Обновлённая модель больше не default — выбрать другую
            self._default = next(
                (n for n, inf in self._info.items() if inf.get("default")),
                next(iter(self._models), ""),
            )

    def vendors(self) -> dict:
        """Return list of vendors"""
        return {vendor.__qualname__: vendor for vendor in self._vendors}


reranking_models_manager = RerankingManager()
