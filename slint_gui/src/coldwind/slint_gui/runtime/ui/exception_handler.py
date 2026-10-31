"""
TODO: currently in discussions !!
handle exception if any thing occurs on the core or slint side !!

core use that contract to use against the rich handle exception interface

core contract demands :-
    def handle_exception(
        self,
        error: Exception,
        context: str = "",
        extra_context: Optional[dict[str, Any]] = None,
    ) -> None:


"""

from typing import Any


class SlintExceptionHandler:

    @classmethod
    def handle_exception(
        self,
        error: Exception,
        context: str = "",
        extra_context: dict[str, Any] | None = None,
    ):
        """
        decided we gonna make that emit the error log to the slint but the slint would gonna show those error logs different way !!
        """

