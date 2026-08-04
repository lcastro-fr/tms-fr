from __future__ import annotations

from collections import Counter
from functools import reduce
from operator import or_

from django.db import models, router, transaction
from django.db.models.deletion import Collector
from django.utils import timezone


class SoftDeleteCollector(Collector):
    """
    El Collector de Django, pero para borrado logico.

    Reutilizamos toda la resolucion de on_delete (CASCADE, PROTECT, RESTRICT,
    SET_NULL, SET_DEFAULT, DO_NOTHING) y el recorrido multinivel del grafo de
    relaciones; lo unico que cambia es que en vez de borrar filas marcamos
    active=False.
    """

    def related_objects(self, related_model, related_fields, objs):
        qs = super().related_objects(related_model, related_fields, objs)
        if issubclass(related_model, BaseModel):
            # Ya esta inactivo: no le volvemos a pisar updated_at ni
            # recorremos su subarbol.
            return qs.actives()
        return qs


def _apply_soft_delete(
    collector: SoftDeleteCollector, using: str, now
) -> tuple[int, dict[str, int]]:
    """Aplica el borrado logico de todo lo que junto el collector."""
    counter: Counter[str] = Counter()
    soft = {"active": False, "updated_at": now}

    with transaction.atomic(using=using, savepoint=False):
        # SET_NULL / SET_DEFAULT / SET(...): esto si es un update real.
        for (field, value), instances_list in collector.field_updates.items():
            querysets = []
            objs = []
            for instances in instances_list:
                if isinstance(instances, models.QuerySet) and instances._result_cache is None:
                    querysets.append(instances)
                else:
                    objs.extend(instances)
            if querysets:
                reduce(or_, querysets).update(**{field.name: value})
            if objs:
                objs[0].__class__._base_manager.using(using).filter(
                    pk__in={obj.pk for obj in objs}
                ).update(**{field.name: value})

        # Hojas que Django resolvio como queryset, sin traer las filas.
        for qs in collector.fast_deletes:
            if not issubclass(qs.model, BaseModel):
                # Sin columna active no hay nada que marcar. La fila del padre
                # sigue existiendo, asi que dejarlo no rompe integridad.
                continue
            count = qs.actives().update(**soft)
            if count:
                counter[qs.model._meta.label] += count

        for model, instances in collector.data.items():
            if not issubclass(model, BaseModel):
                continue
            pks = {obj.pk for obj in instances}
            if not pks:
                continue
            count = model._base_manager.using(using).filter(pk__in=pks).actives().update(**soft)
            if count:
                counter[model._meta.label] += count

    return sum(counter.values()), dict(counter)


class ActivosQuerySet(models.QuerySet):
    def actives(self) -> "ActivosQuerySet":
        return self.filter(active=True)

    def inactives(self) -> "ActivosQuerySet":
        return self.filter(active=False)

    def delete(self) -> tuple[int, dict[str, int]]:
        # Mismas restricciones que QuerySet.delete().
        self._not_support_combined_queries("delete")
        if self.query.is_sliced:
            raise TypeError("Cannot use 'limit' or 'offset' with delete().")
        if self.query.distinct_fields:
            raise TypeError("Cannot call delete() after .distinct(*fields).")
        if self._fields is not None:
            raise TypeError("Cannot call delete() after .values() or .values_list()")

        del_query = self._chain()
        del_query._for_write = True
        del_query.query.select_for_update = False
        del_query.query.select_related = False
        del_query.query.clear_ordering(force=True)

        collector = SoftDeleteCollector(using=del_query.db, origin=self)
        collector.collect(del_query)
        result = _apply_soft_delete(collector, del_query.db, timezone.now())

        self._result_cache = None
        return result

    delete.alters_data = True
    # Evita que exista Model.objects.delete(), que borraria toda la tabla.
    delete.queryset_only = True


BaseManager = models.Manager.from_queryset(ActivosQuerySet)


class ActivesManager(BaseManager):
    def get_queryset(self) -> ActivosQuerySet:
        return super().get_queryset().actives()


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)

    # El orden importa: el primero declarado es el _default_manager.
    objects = ActivesManager()
    all_objects = BaseManager()

    class Meta:
        abstract = True
        # Las internals de Django (FK hacia adelante, refresh_from_db,
        # collector de cascade) usan _base_manager: debe quedar sin filtrar.
        base_manager_name = "all_objects"

    def delete(self, using=None, keep_parents=False) -> tuple[int, dict[str, int]]:
        if self.pk is None:
            raise ValueError(
                f"{self._meta.object_name} object can't be deleted because its "
                f"{self._meta.pk.attname} attribute is set to None."
            )
        using = using or router.db_for_write(self.__class__, instance=self)
        now = timezone.now()

        collector = SoftDeleteCollector(using=using, origin=self)
        collector.collect([self], keep_parents=keep_parents)
        result = _apply_soft_delete(collector, using, now)

        self.active = False
        self.updated_at = now
        return result

    delete.alters_data = True
