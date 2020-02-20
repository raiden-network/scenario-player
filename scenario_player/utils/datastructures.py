from typing import Any, Callable, Generic, Iterable, List, NoReturn, Optional, TypeVar, Union

T = TypeVar("T")


class FrozenList(list, Generic[T]):
    """An immutable list."""

    def _not_supported(self) -> NoReturn:
        raise TypeError(f"Can't modify {self.__class__.__name__}")

    def __setitem__(self, *args, **kwargs) -> NoReturn:
        self._not_supported()

    def __delitem__(self, i: Union[int, slice]) -> NoReturn:
        self._not_supported()

    def __iadd__(self, x: Iterable[T]) -> NoReturn:
        self._not_supported()

    def __imul__(self, n: int) -> NoReturn:
        self._not_supported()

    def append(self, obj: T) -> NoReturn:  # pylint: disable=unused-argument
        self._not_supported()

    def clear(self) -> NoReturn:
        self._not_supported()

    def extend(self, iterable: Iterable[T]) -> NoReturn:  # pylint: disable=unused-argument
        self._not_supported()

    def insert(self, index: int, item: T) -> NoReturn:  # pylint: disable=unused-argument
        self._not_supported()

    def pop(self, index: int = 0) -> NoReturn:  # pylint: disable=unused-argument
        self._not_supported()

    def remove(self, obj: T) -> NoReturn:  # pylint: disable=unused-argument
        self._not_supported()

    def reverse(self) -> NoReturn:
        self._not_supported()

    def sort(  # pylint: disable=unused-argument
        self, *, key: Optional[Callable[[T], Any]] = None, reverse: bool = False
    ) -> NoReturn:
        self._not_supported()

    def __hash__(self) -> int:
        return hash(repr(self))

    def __add__(self, x: List[T]) -> FrozenList[T]:
        return self.__class__(super().__add__(x))

    def __mul__(self, n: int) -> FrozenList[T]:
        return self.__class__(super().__mul__(n))

    def __rmul__(self, n: int) -> FrozenList[T]:
        return self.__class__(super().__rmul__(n))

    def __repr__(self) -> str:
        return f"<FrozenList({super().__repr__()})>"

    def copy(self) -> List[T]:
        return self
