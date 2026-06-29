"""Tipe data transkrip yang netral terhadap engine."""

from dataclasses import dataclass, field


@dataclass
class TranscriptWord:
    word: str
    start: float
    end: float


@dataclass
class Transcript:
    language: str
    text: str
    words: list[TranscriptWord] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "language": self.language,
            "text": self.text,
            "words": [{"word": w.word, "start": w.start, "end": w.end} for w in self.words],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Transcript":
        return cls(
            language=data.get("language", ""),
            text=data.get("text", ""),
            words=[TranscriptWord(**w) for w in data.get("words", [])],
        )
