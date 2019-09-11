from __future__ import annotations

from typing import _T, Any, Callable, Iterable, Iterator, List, NoReturn, Optional, Union


class FrozenList(list):
    """An immutable list."""

    def _not_supported(self) -> NoReturn:
        raise TypeError(f"Can't modify {self.__class__.__name__}")

    def __setitem__(self, *args, **kwargs) -> NoReturn:
        self._not_supported()

    def __delitem__(self, i: Union[int, slice]) -> NoReturn:
        self._not_supported()

    def __iadd__(self, x: Iterable[_T]) -> NoReturn:
        self._not_supported()

    def __imul__(self, n: int) -> NoReturn:
        self._not_supported()

    def append(self, obj: _T) -> NoReturn:
        self._not_supported()

    def clear(self) -> NoReturn:
        self._not_supported()

    def extend(self, iterable: Iterable[_T]) -> NoReturn:
        self._not_supported()

    def insert(self, index: int, object: _T) -> NoReturn:
        self._not_supported()

    def pop(self, index: int = 0) -> NoReturn:
        self._not_supported()

    def remove(self, obj: _T) -> NoReturn:
        self._not_supported()

    def reverse(self) -> NoReturn:
        self._not_supported()

    def sort(
        self, *, key: Optional[Callable[[_T], Any]] = None, reverse: bool = False
    ) -> NoReturn:
        self._not_supported()

    def __hash__(self) -> int:
        return hash(repr(self))

    def __add__(self, x: List[_T]) -> FrozenList[_T]:
        return self.__class__(super().__add__(x))

    def __mul__(self, n: int) -> FrozenList[_T]:
        return self.__class__(super().__mul__(n))

    def __rmul__(self, n: int) -> FrozenList[_T]:
        return self.__class__(super().__rmul__(n))

    def __reversed__(self) -> Iterator[_T]:
        return self.__class__(super().__reversed__())

    def __repr__(self) -> str:
        return f"<FrozenList({super().__repr__()})>"

    def copy(self) -> List[_T]:
        return self
