from pydantic import BaseModel

from .time import EPOCH, UTC_NOW


class Metric(BaseModel):
    name: str
    interval: int
    value: float
    tags: list[str]
    time: int

    @classmethod
    def create(
        cls, name: str, interval: int, value: float, tags: list[str]
    ) -> "Metric":
        return cls(
            name=name,
            interval=interval,
            value=value,
            tags=tags,
            time=int((UTC_NOW() - EPOCH).total_seconds()),
        )

    @staticmethod
    def tag(key: str, value: str) -> str:
        return f"{key}={value}"


class MetricCounter:
    def __init__(self, name: str, tags: list[str], initial_value: int = 0) -> None:
        self.name = name
        self.tags = tags
        self.value = initial_value
        self._start_time = UTC_NOW()

    def measure(self, value: int) -> None:
        self.value += value

    def report(self, new_initial_value: int = 0) -> list[Metric]:
        metric = Metric.create(
            f"{self.name}.c",
            int((UTC_NOW() - self._start_time).total_seconds()),
            self.value,
            self.tags,
        )
        return [metric]

    def reset(self, new_initial_value: int = 0) -> None:
        self._start_time = UTC_NOW()
        self.value = new_initial_value


class MetricSummary:
    def __init__(self, name: str, tags: list[str]) -> None:
        self.name = name
        self.tags = tags
        self.value = 0
        self._samples = 0
        self._min = None
        self._max = None
        self._start_time = UTC_NOW()

    def measure(self, value: int) -> None:
        self.value += value
        self._samples += 1
        if self._min is None:
            self._min = value
        if self._max is None:
            self._max = value
        self._min = min(self._min, value)
        self._max = max(self._max, value)

    def report(self) -> list[Metric]:
        metrics: list[Metric] = []
        duration = int((UTC_NOW() - self._start_time).total_seconds())
        if self._samples > 0:
            metrics.append(
                Metric.create(
                    f"{self.name}.avg",
                    duration,
                    self.value / self._samples,
                    self.tags,
                )
            )
            metrics.append(
                Metric.create(
                    f"{self.name}.min",
                    duration,
                    self._min,
                    self.tags,
                )
            )
            metrics.append(
                Metric.create(
                    f"{self.name}.max",
                    duration,
                    self._max,
                    self.tags,
                )
            )
            metrics.append(
                Metric.create(
                    f"{self.name}.count",
                    duration,
                    self._samples,
                    self.tags,
                )
            )
        return metrics

    def reset(self) -> None:
        self.value = 0
        self._start_time = UTC_NOW()
        self._min = None
        self._max = None
        self._samples = 0
