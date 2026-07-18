from dataclasses import dataclass, field
from pathlib import Path
from typing import Final


DATASET_NAME: Final[str] = "Trever896/openbrush-75k"
DATASET_SPLIT: Final[str] = "train"
DATASET_VERSION: Final[str] = "1.0.0"
DATASET_OUTPUT_NAME: Final[str] = "Aegis-Art-Atelier-22K"

TARGET_WIDTH: Final[int] = 896
TARGET_HEIGHT: Final[int] = 896
TARGET_SIZE: Final[tuple[int, int]] = (TARGET_WIDTH, TARGET_HEIGHT)

JPEG_FORMAT: Final[str] = "JPEG"
JPEG_QUALITY: Final[int] = 90

DEFAULT_OUTPUT_DIR: Final[Path] = Path("/content/aegis_art_atelier_22k")
DEFAULT_LOG_FILENAME: Final[str] = "etl.log"
DEFAULT_MANIFEST_FILENAME: Final[str] = "manifest.jsonl"
DEFAULT_DATASET_INFO_FILENAME: Final[str] = "dataset_info.json"
DEFAULT_STATS_FILENAME: Final[str] = "stats.json"

DEFAULT_RANDOM_SEED: Final[int] = 42
DEFAULT_LOG_INTERVAL: Final[int] = 2_000

# Style caps are based on the audited OpenBrush-75K distribution.
# Major styles use a cap of 1,000. Minor style values represent their
# audited available population and therefore preserve the expected
# approximately 22,000-image output size.
STYLE_CAPS: Final[dict[str, int]] = {
    "Impressionism": 1_000,
    "Realism": 1_000,
    "Romanticism": 1_000,
    "Post": 1_000,
    "Expressionism": 1_000,
    "Baroque": 1_000,
    "Art": 1_000,
    "Symbolism": 1_000,
    "Northern": 1_000,
    "Abstract": 1_000,
    "Rococo": 1_000,
    "Cubism": 1_000,
    "Color": 1_000,
    "Early": 1_000,
    "Pop": 1_000,
    "High": 1_000,
    "Minimalism": 1_000,
    "Naive": 1_000,
    "Mannerism": 1_000,
    "Ukiyo": 1_000,
    "Fauvism": 870,
    "Pointillism": 505,
    "Contemporary": 471,
    "New": 314,
    "Action": 98,
}

# Styles are normalized before cap evaluation.
STYLE_MERGE: Final[dict[str, str]] = {
    "Synthetic": "Cubism",
}

# Excluded styles are discarded before reservoir sampling.
STYLE_EXCLUDE: Final[frozenset[str]] = frozenset(
    {
        "Analytical",
    }
)

# Candidate fields used to construct a caption from the source record.
CAPTION_FIELD_CANDIDATES: Final[tuple[str, ...]] = (
    "subject",
    "action",
    "setting",
    "mood",
    "lighting",
    "color",
    "composition",
    "style_description",
    "caption",
)

MIN_CAPTION_WORDS: Final[int] = 25
MIN_CAPTION_CHARACTERS: Final[int] = 120


@dataclass(slots=True)
class ETLConfig:
    """Runtime configuration for the Aegis-Art-Atelier ETL pipeline.

    Attributes:
        output_dir: Directory where images and metadata are written.
        seed: Random seed used by reservoir sampling.
        dry_run: Optional maximum number of streamed records to inspect.
        log_every: Progress-report interval measured in streamed records.
        drive_output: Optional directory for copying the final archive.
        dataset_name: Hugging Face dataset identifier.
        dataset_split: Dataset split to stream.
        target_size: Final output image dimensions.
        jpeg_quality: JPEG encoding quality.
        min_caption_words: Minimum accepted caption word count.
        min_caption_characters: Minimum accepted caption character count.
    """

    output_dir: Path = field(default_factory=lambda: DEFAULT_OUTPUT_DIR)
    seed: int = DEFAULT_RANDOM_SEED
    dry_run: int | None = None
    log_every: int = DEFAULT_LOG_INTERVAL
    drive_output: Path | None = None

    dataset_name: str = DATASET_NAME
    dataset_split: str = DATASET_SPLIT
    target_size: tuple[int, int] = TARGET_SIZE
    jpeg_quality: int = JPEG_QUALITY
    min_caption_words: int = MIN_CAPTION_WORDS
    min_caption_characters: int = MIN_CAPTION_CHARACTERS

    def __post_init__(self) -> None:
        """Validate and normalize configuration values."""
        self.output_dir = Path(self.output_dir)

        if self.drive_output is not None:
            self.drive_output = Path(self.drive_output)

        if self.seed < 0:
            raise ValueError("The random seed must be zero or greater.")

        if self.dry_run is not None and self.dry_run <= 0:
            raise ValueError("dry_run must be greater than zero when provided.")

        if self.log_every <= 0:
            raise ValueError("log_every must be greater than zero.")

        if len(self.target_size) != 2:
            raise ValueError("target_size must contain width and height.")

        width, height = self.target_size
        if width <= 0 or height <= 0:
            raise ValueError("Image dimensions must be greater than zero.")

        if not 1 <= self.jpeg_quality <= 100:
            raise ValueError("jpeg_quality must be between 1 and 100.")

        if self.min_caption_words < 0:
            raise ValueError("min_caption_words cannot be negative.")

        if self.min_caption_characters < 0:
            raise ValueError("min_caption_characters cannot be negative.")

    @property
    def images_dir(self) -> Path:
        """Return the directory used for processed JPEG images."""
        return self.output_dir / "images"

    @property
    def manifest_path(self) -> Path:
        """Return the manifest JSONL output path."""
        return self.output_dir / DEFAULT_MANIFEST_FILENAME

    @property
    def dataset_info_path(self) -> Path:
        """Return the dataset metadata output path."""
        return self.output_dir / DEFAULT_DATASET_INFO_FILENAME

    @property
    def stats_path(self) -> Path:
        """Return the statistics output path."""
        return self.output_dir / DEFAULT_STATS_FILENAME

    @property
    def log_path(self) -> Path:
        """Return the ETL log output path."""
        return self.output_dir / DEFAULT_LOG_FILENAME

    @property
    def archive_path(self) -> Path:
        """Return the default compressed dataset archive path."""
        return self.output_dir.parent / f"{self.output_dir.name}.tar.gz"