"""Setup 向导业务异常。"""

from __future__ import annotations

from uuid import UUID


class MaterialsInsufficientError(ValueError):
    """品牌资料不足以生成微观利基画像。"""

    code = "materials_insufficient"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class SubjectDuplicateError(ValueError):
    """同租户下 domain/brand 监测主体已存在。"""

    code = "subject_duplicate"

    def __init__(self, message: str, *, existing_subject_id: UUID | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.existing_subject_id = existing_subject_id
