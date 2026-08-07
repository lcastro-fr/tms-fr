from __future__ import annotations

from transportista.models import ConceptoAdicional


class ConceptoAdicionalService:
    @staticmethod
    def list_conceptos() -> list[ConceptoAdicional]:
        return list(ConceptoAdicional.objects.all())
