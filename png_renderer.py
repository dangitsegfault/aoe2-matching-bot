from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont


Size = int | float | str | None
BorderWidth = int | tuple[int, int, int, int]


def resolve_size(
    value: Size,
    parent_size: int | None,
) -> int | None:
    """
    Resolve a size specification.

    Examples:
        200      -> 200 pixels
        "50%"    -> 50% of parent_size
        None     -> auto/intrinsic size
    """
    if value is None:
        return None

    if isinstance(value, str):
        if not value.endswith("%"):
            raise ValueError(
                f"Invalid size {value!r}. "
                "Expected a number or percentage such as '50%'."
            )

        if parent_size is None:
            raise ValueError(
                f"Cannot resolve percentage size {value!r} "
                "without a parent size."
            )

        try:
            percentage = float(value[:-1])
        except ValueError:
            raise ValueError(
                f"Invalid percentage size: {value!r}"
            )

        return round(parent_size * percentage / 100)

    return round(value)


class Node:
    def __init__(
        self,
        *,
        width: Size = None,
        height: Size = None,
        align_self: str | None = None,
    ):
        self.parent: Container | None = None

        # Requested size.
        self.width = width
        self.height = height

        # Resolved layout geometry.
        self.x = 0
        self.y = 0
        self.actual_width = 0
        self.actual_height = 0

        self.align_self = align_self

    def measure(
        self,
        parent_width: int | None = None,
        parent_height: int | None = None,
    ) -> tuple[int, int]:
        raise NotImplementedError

    def layout(
        self,
        parent_width: int | None = None,
        parent_height: int | None = None,
    ) -> None:
        measured_width, measured_height = self.measure(
            parent_width,
            parent_height,
        )

        width = resolve_size(
            self.width,
            parent_width,
        )

        height = resolve_size(
            self.height,
            parent_height,
        )

        self.actual_width = (
            width if width is not None else measured_width
        )

        self.actual_height = (
            height if height is not None else measured_height
        )

    def draw(self, canvas: Image.Image) -> None:
        raise NotImplementedError


class Container(Node):
    def __init__(
        self,
        *,
        width: Size = None,
        height: Size = None,
        children: list[Node] | None = None,
        direction: str = "column",
        justify: str = "start",
        align: str = "start",
        gap: int = 0,
        padding: int = 0,
        background=None,
        border_width: BorderWidth = 0,
        border_color=(0, 0, 0, 255),
        border_sides: set[str] | None = None,
    ):
        super().__init__(
            width=width,
            height=height,
        )

        if direction not in ("row", "column"):
            raise ValueError(
                "direction must be 'row' or 'column'"
            )

        if justify not in (
            "start",
            "center",
            "end",
            "space_between",
            "space_around",
        ):
            raise ValueError(
                "invalid justify value"
            )

        if align not in (
            "start",
            "center",
            "end",
        ):
            raise ValueError(
                "align must be 'start', 'center', or 'end'"
            )

        if gap < 0:
            raise ValueError(
                "gap must be >= 0"
            )

        if padding < 0:
            raise ValueError(
                "padding must be >= 0"
            )

        # Normalize border width to:
        #
        #     (top, right, bottom, left)
        #
        if isinstance(border_width, int):
            if border_width < 0:
                raise ValueError(
                    "border_width must be >= 0"
                )

            border_width = (
                border_width,
                border_width,
                border_width,
                border_width,
            )

        else:
            if len(border_width) != 4:
                raise ValueError(
                    "border_width must be an int or "
                    "(top, right, bottom, left)"
                )

            if any(
                width < 0
                for width in border_width
            ):
                raise ValueError(
                    "border_width values must be >= 0"
                )

        valid_sides = {
            "top",
            "right",
            "bottom",
            "left",
        }

        if border_sides is None:
            border_sides = valid_sides.copy()
        else:
            border_sides = set(border_sides)

            invalid_sides = (
                border_sides - valid_sides
            )

            if invalid_sides:
                raise ValueError(
                    f"invalid border sides: "
                    f"{invalid_sides}"
                )

        self.children: list[Node] = []

        self.direction = direction
        self.justify = justify
        self.align = align
        self.gap = gap
        self.padding = padding

        self.background = background

        self.border_width = border_width
        self.border_color = border_color
        self.border_sides = border_sides

        for child in children or []:
            self.add(child)

    def add(self, child: Node) -> None:
        child.parent = self
        self.children.append(child)

    def _intrinsic_size(
        self,
        parent_width: int | None,
        parent_height: int | None,
    ) -> tuple[int, int]:
        """
        Calculate the natural size of this container.

        parent_width / parent_height are the dimensions available
        from the parent. They are used to resolve percentage sizes.
        """
        if not self.children:
            return (
                self.padding * 2,
                self.padding * 2,
            )

        sizes = [
            child.measure(
                parent_width,
                parent_height,
            )
            for child in self.children
        ]

        if self.direction == "row":
            width = (
                sum(w for w, _ in sizes)
                + self.gap * (len(sizes) - 1)
            )

            height = max(
                h for _, h in sizes
            )

        else:
            width = max(
                w for w, _ in sizes
            )

            height = (
                sum(h for _, h in sizes)
                + self.gap * (len(sizes) - 1)
            )

        return (
            width + self.padding * 2,
            height + self.padding * 2,
        )

    def measure(
        self,
        parent_width: int | None = None,
        parent_height: int | None = None,
    ) -> tuple[int, int]:
        """
        Determine this container's size.

        If width/height are explicitly specified, resolve them first.
        Those resolved dimensions are then used as the basis for
        percentage-sized children.
        """
        width = resolve_size(
            self.width,
            parent_width,
        )

        height = resolve_size(
            self.height,
            parent_height,
        )

        child_parent_width = (
            max(
                0,
                width - self.padding * 2,
            )
            if width is not None
            else parent_width
        )

        child_parent_height = (
            max(
                0,
                height - self.padding * 2,
            )
            if height is not None
            else parent_height
        )

        intrinsic_width, intrinsic_height = (
            self._intrinsic_size(
                child_parent_width,
                child_parent_height,
            )
        )

        return (
            width if width is not None else intrinsic_width,
            height if height is not None else intrinsic_height,
        )

    def _resolve_child_size(
        self,
        child: Node,
        content_width: int,
        content_height: int,
    ) -> tuple[int, int]:
        """
        Resolve a child's final size.

        Percentage dimensions are relative to this container's
        content area.
        """
        measured_width, measured_height = child.measure(
            content_width,
            content_height,
        )

        width = resolve_size(
            child.width,
            content_width,
        )

        height = resolve_size(
            child.height,
            content_height,
        )

        if width is None:
            width = measured_width

        if height is None:
            height = measured_height

        return width, height

    def _justify(
        self,
        available: int,
        sizes: list[int],
    ) -> tuple[float, float]:
        """
        Returns:

            start_offset:
                Position of the first child.

            spacing:
                Additional space between children.
        """
        if not sizes:
            return 0, 0

        total = sum(sizes)
        remaining = available - total

        if self.justify == "center":
            return remaining / 2, 0

        if self.justify == "end":
            return remaining, 0

        if self.justify == "space_between":
            if len(sizes) == 1:
                return 0, 0

            return (
                0,
                remaining / (len(sizes) - 1),
            )

        if self.justify == "space_around":
            spacing = remaining / len(sizes)

            return (
                spacing / 2,
                spacing,
            )

        return 0, 0

    def _cross_position(
        self,
        alignment: str,
        available: int,
        size: int,
    ) -> float:
        remaining = available - size

        if alignment == "center":
            return remaining / 2

        if alignment == "end":
            return remaining

        return 0

    def layout(
        self,
        parent_width: int | None = None,
        parent_height: int | None = None,
    ) -> None:
        measured_width, measured_height = self.measure(
            parent_width,
            parent_height,
        )

        self.actual_width = (
            resolve_size(
                self.width,
                parent_width,
            )
            if self.width is not None
            else measured_width
        )

        self.actual_height = (
            resolve_size(
                self.height,
                parent_height,
            )
            if self.height is not None
            else measured_height
        )

        # Content box.
        content_width = max(
            0,
            self.actual_width - self.padding * 2,
        )

        content_height = max(
            0,
            self.actual_height - self.padding * 2,
        )

        # Resolve all child sizes against the content box.
        sizes = [
            self._resolve_child_size(
                child,
                content_width,
                content_height,
            )
            for child in self.children
        ]

        if self.direction == "row":
            main_sizes = [
                width
                for width, _ in sizes
            ]

            fixed_gap = self.gap * max(
                0,
                len(main_sizes) - 1,
            )

            start, spacing = self._justify(
                content_width - fixed_gap,
                main_sizes,
            )

            main_position = start

            for child, (
                child_width,
                child_height,
            ) in zip(self.children, sizes):

                alignment = (
                    child.align_self
                    if child.align_self is not None
                    else self.align
                )

                cross_position = self._cross_position(
                    alignment,
                    content_height,
                    child_height,
                )

                child.x = (
                    self.x
                    + self.padding
                    + main_position
                )

                child.y = (
                    self.y
                    + self.padding
                    + cross_position
                )

                child.actual_width = child_width
                child.actual_height = child_height

                main_position += (
                    child_width
                    + self.gap
                    + spacing
                )

        else:
            main_sizes = [
                height
                for _, height in sizes
            ]

            fixed_gap = self.gap * max(
                0,
                len(main_sizes) - 1,
            )

            start, spacing = self._justify(
                content_height - fixed_gap,
                main_sizes,
            )

            main_position = start

            for child, (
                child_width,
                child_height,
            ) in zip(self.children, sizes):

                alignment = (
                    child.align_self
                    if child.align_self is not None
                    else self.align
                )

                cross_position = self._cross_position(
                    alignment,
                    content_width,
                    child_width,
                )

                child.x = (
                    self.x
                    + self.padding
                    + cross_position
                )

                child.y = (
                    self.y
                    + self.padding
                    + main_position
                )

                child.actual_width = child_width
                child.actual_height = child_height

                main_position += (
                    child_height
                    + self.gap
                    + spacing
                )

        # Recursively lay out nested containers.
        for child in self.children:
            if isinstance(child, Container):
                child.layout(
                    child.actual_width,
                    child.actual_height,
                )

    def draw(self, canvas: Image.Image) -> None:
        draw = ImageDraw.Draw(canvas)

        x0 = int(self.x)
        y0 = int(self.y)

        x1 = int(
            self.x
            + self.actual_width
            - 1
        )

        y1 = int(
            self.y
            + self.actual_height
            - 1
        )

        # Background.
        if (
            self.background is not None
            and self.actual_width > 0
            and self.actual_height > 0
        ):
            draw.rectangle(
                (
                    x0,
                    y0,
                    x1,
                    y1,
                ),
                fill=self.background,
            )

        # Children.
        for child in self.children:
            child.draw(canvas)

        # Border.
        top, right, bottom, left = self.border_width

        if "top" in self.border_sides and top > 0:
            draw.rectangle(
                (
                    x0,
                    y0,
                    x1,
                    y0 + top - 1,
                ),
                fill=self.border_color,
            )

        if "right" in self.border_sides and right > 0:
            draw.rectangle(
                (
                    x1 - right + 1,
                    y0,
                    x1,
                    y1,
                ),
                fill=self.border_color,
            )

        if "bottom" in self.border_sides and bottom > 0:
            draw.rectangle(
                (
                    x0,
                    y1 - bottom + 1,
                    x1,
                    y1,
                ),
                fill=self.border_color,
            )

        if "left" in self.border_sides and left > 0:
            draw.rectangle(
                (
                    x0,
                    y0,
                    x0 + left - 1,
                    y1,
                ),
                fill=self.border_color,
            )

    def render(
        self,
        path: str,
        *,
        background=(255, 255, 255, 255),
    ) -> None:
        width, height = self.measure()

        self.actual_width = width
        self.actual_height = height

        self.x = 0
        self.y = 0

        canvas = Image.new(
            "RGBA",
            (width, height),
            background,
        )

        self.layout()

        self.draw(canvas)

        canvas.save(path)


class Text(Node):
    def __init__(
        self,
        text: str,
        font: ImageFont.FreeTypeFont,
        *,
        width: Size = None,
        height: Size = None,
        fill=(255, 255, 255, 255),
        align_self: str | None = None,
    ):
        super().__init__(
            width=width,
            height=height,
            align_self=align_self,
        )

        self.text = text
        self.font = font
        self.fill = fill

    def measure(
        self,
        parent_width: int | None = None,
        parent_height: int | None = None,
    ) -> tuple[int, int]:
        dummy = Image.new(
            "RGBA",
            (1, 1),
        )

        draw = ImageDraw.Draw(dummy)

        bbox = draw.textbbox(
            (0, 0),
            self.text,
            font=self.font,
        )

        intrinsic_width = bbox[2] - bbox[0]
        intrinsic_height = bbox[3] - bbox[1]

        width = resolve_size(
            self.width,
            parent_width,
        )

        height = resolve_size(
            self.height,
            parent_height,
        )

        return (
            width if width is not None else intrinsic_width,
            height if height is not None else intrinsic_height,
        )

    def draw(self, canvas: Image.Image) -> None:
        draw = ImageDraw.Draw(canvas)

        draw.text(
            (
                int(self.x),
                int(self.y),
            ),
            self.text,
            font=self.font,
            fill=self.fill,
        )


class ImageNode(Node):
    def __init__(
        self,
        image: str | Image.Image,
        *,
        width: Size = None,
        height: Size = None,
        scale: float = 1.0,
        align_self: str | None = None,
    ):
        super().__init__(
            width=width,
            height=height,
            align_self=align_self,
        )

        if scale <= 0:
            raise ValueError(
                "scale must be greater than 0"
            )

        self.scale = scale

        if isinstance(image, Image.Image):
            self.image = image.convert("RGBA")
        else:
            self.image = Image.open(image).convert("RGBA")

    def measure(
        self,
        parent_width: int | None = None,
        parent_height: int | None = None,
    ) -> tuple[int, int]:
        width = resolve_size(
            self.width,
            parent_width,
        )

        height = resolve_size(
            self.height,
            parent_height,
        )

        # Scale intrinsic dimensions.
        if width is None:
            width = round(
                self.image.width * self.scale
            )

        if height is None:
            height = round(
                self.image.height * self.scale
            )

        return width, height

    def draw(self, canvas: Image.Image) -> None:
        image = self.image

        if (
            image.width != self.actual_width
            or image.height != self.actual_height
        ):
            image = image.resize(
                (
                    self.actual_width,
                    self.actual_height,
                ),
                Image.Resampling.LANCZOS,
            )

        canvas.alpha_composite(
            image,
            (
                int(self.x),
                int(self.y),
            ),
        )
