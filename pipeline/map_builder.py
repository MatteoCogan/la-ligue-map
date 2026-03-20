"""
Generate filtered GeoGuessr maps from the pipeline output.
"""

from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Set

from pydantic import BaseModel, Field, validator

from config import DATA_DIR, OUTPUT_FILE
from logger import setup_logger
from models import Coordinate, MapData
from uploader import Uploader

logger = setup_logger(__name__)


def _normalize_token(value: str) -> str:
    """Normalize values for case-insensitive exact matching."""
    return value.strip().casefold()


def _normalize_mode(value: str) -> str:
    """Normalize common GeoGuessr mode variants to a stable tag."""
    normalized = _normalize_token(value)

    if normalized in {"nm", "no move", "no-move", "nomove"}:
        return "NM"
    if normalized == "move":
        return "Move"
    if normalized == "nmpz":
        return "NMPZ"
    if normalized == "npz":
        return "NPZ"
    if normalized == "nms":
        return "NMS"

    if value.isupper():
        return value.strip()

    return value.strip().title()


def _slugify(value: str) -> str:
    """Build a filesystem-friendly slug from a map name."""
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return slug or "generated-map"


class MapFilterSpec(BaseModel):
    """Filtering parameters for map generation."""

    sources: List[str] = Field(default_factory=list)
    seasons: List[str] = Field(default_factory=list)
    divisions: List[str] = Field(default_factory=list)
    journeys: List[str] = Field(default_factory=list)
    modes: List[str] = Field(default_factory=list)
    countries: List[str] = Field(default_factory=list)
    country_codes: List[str] = Field(default_factory=list)
    state_codes: List[str] = Field(default_factory=list)
    include_tags_all: List[str] = Field(default_factory=list)
    include_tags_any: List[str] = Field(default_factory=list)
    exclude_tags_any: List[str] = Field(default_factory=list)
    text_contains_any: List[str] = Field(default_factory=list)
    link_ids: List[str] = Field(default_factory=list)
    sample_size: Optional[int] = None
    sample_seed: int = 42
    limit: Optional[int] = None

    @validator("sample_size", "limit")
    def validate_positive_optional_int(cls, value: Optional[int]) -> Optional[int]:
        """Ensure positive values when provided."""
        if value is not None and value <= 0:
            raise ValueError("Value must be > 0")
        return value

    @validator("sample_seed")
    def validate_sample_seed(cls, value: int) -> int:
        """Keep the seed deterministic."""
        return int(value)


class MapBuildSpec(BaseModel):
    """Single map generation specification."""

    name: str
    source_file: Optional[Path] = None
    output_file: Optional[Path] = None
    upload: bool = False
    map_id: Optional[str] = None
    public_url: Optional[str] = None
    chunk_size: int = 500
    filters: MapFilterSpec = Field(default_factory=MapFilterSpec)

    @validator("chunk_size")
    def validate_chunk_size(cls, value: int) -> int:
        """Chunk size must stay positive."""
        if value <= 0:
            raise ValueError("chunk_size must be > 0")
        return value


class MapBatchSpec(BaseModel):
    """Batch generation specification."""

    maps: List[MapBuildSpec] = Field(default_factory=list)


@dataclass
class BuildResult:
    """Result of one generated map."""

    spec: MapBuildSpec
    map_data: MapData
    output_file: Path
    source_count: int
    selected_count: int
    uploaded_map_id: Optional[str] = None


class MapBuilder:
    """Generate filtered maps from a transformed pipeline JSON file."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    def load_map_data(self, source_file: Optional[Path] = None) -> MapData:
        """Load a transformed map JSON from disk."""
        source_path = Path(source_file) if source_file else OUTPUT_FILE

        with open(source_path, "r", encoding="utf-8") as file_handle:
            raw_data = json.load(file_handle)

        return MapData(**raw_data)

    def build_map(self, spec: MapBuildSpec) -> BuildResult:
        """Build one filtered map from the input file."""
        source_map = self.load_map_data(spec.source_file)
        filtered_coordinates = self._filter_coordinates(
            source_map.customCoordinates,
            spec.filters,
        )

        generated_map = MapData(
            name=spec.name,
            customCoordinates=filtered_coordinates,
        )

        output_file = self._resolve_output_path(spec)

        return BuildResult(
            spec=spec,
            map_data=generated_map,
            output_file=output_file,
            source_count=len(source_map.customCoordinates),
            selected_count=len(filtered_coordinates),
        )

    def save_result(self, result: BuildResult) -> None:
        """Persist a generated map to disk."""
        result.output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(result.output_file, "w", encoding="utf-8") as file_handle:
            json.dump(
                result.map_data.dict(),
                file_handle,
                indent=2,
                ensure_ascii=False,
                default=str,
            )

        logger.info(
            "Map generee: %s (%s/%s coordonnees)",
            result.output_file,
            result.selected_count,
            result.source_count,
        )

    def upload_result(self, result: BuildResult) -> Optional[str]:
        """Upload a generated map to map-making.app."""
        if not result.spec.upload:
            return None

        if not result.map_data.customCoordinates:
            logger.warning(
                "Upload ignore pour '%s': aucune coordonnee selectionnee",
                result.map_data.name,
            )
            return None

        uploader = Uploader(self.api_key)
        if not uploader.test_connection():
            raise RuntimeError("Connexion API impossible")

        map_id = result.spec.map_id
        if not map_id:
            map_id = uploader.create_map(
                result.map_data.name,
                public_url=result.spec.public_url,
            )
        elif result.spec.public_url:
            uploader._update_map_url(map_id, result.map_data.name, result.spec.public_url)

        if not uploader.clear_map_locations(map_id):
            raise RuntimeError(f"Impossible de vider la map {map_id}")

        coordinates = result.map_data.customCoordinates
        if len(coordinates) > result.spec.chunk_size:
            success = uploader.batch_import_by_chunks(
                map_id,
                coordinates,
                chunk_size=result.spec.chunk_size,
            )
        else:
            success = uploader.import_locations(map_id, coordinates)

        if not success:
            raise RuntimeError(f"Import echoue pour la map {map_id}")

        logger.info("Map uploadée: %s -> %s", result.map_data.name, map_id)
        result.uploaded_map_id = map_id
        return map_id

    def build_from_batch_file(self, batch_file: Path) -> List[BuildResult]:
        """Load a batch spec JSON and generate each map."""
        with open(batch_file, "r", encoding="utf-8") as file_handle:
            raw_data = json.load(file_handle)

        batch_spec = MapBatchSpec(**raw_data)
        results: List[BuildResult] = []

        for spec in batch_spec.maps:
            result = self.build_map(spec)
            self.save_result(result)
            if spec.upload:
                self.upload_result(result)
            results.append(result)

        return results

    def _resolve_output_path(self, spec: MapBuildSpec) -> Path:
        """Return the output path for a generated map."""
        if spec.output_file:
            return Path(spec.output_file)

        return DATA_DIR / "generated" / f"{_slugify(spec.name)}.json"

    def _filter_coordinates(
        self,
        coordinates: Sequence[Coordinate],
        filters: MapFilterSpec,
    ) -> List[Coordinate]:
        """Apply all filters and optional sampling."""
        selected = [
            coordinate
            for coordinate in coordinates
            if self._matches_filters(coordinate, filters)
        ]

        if filters.sample_size and filters.sample_size < len(selected):
            randomizer = random.Random(filters.sample_seed)
            indexed_selection = list(enumerate(selected))
            sampled_entries = randomizer.sample(indexed_selection, filters.sample_size)
            selected = [coord for _, coord in sorted(sampled_entries, key=lambda item: item[0])]

        if filters.limit:
            selected = selected[: filters.limit]

        return selected

    def _matches_filters(self, coordinate: Coordinate, filters: MapFilterSpec) -> bool:
        """Return True when a coordinate matches the full filter set."""
        tags = coordinate.extra.tags or []
        tags_normalized = {_normalize_token(tag) for tag in tags}
        link_ids = {
            _normalize_token(tag.split("=", 1)[1])
            for tag in tags
            if tag.startswith("link=") and "=" in tag
        }
        searchable_parts = list(tags)
        if coordinate.countryCode:
            searchable_parts.append(coordinate.countryCode)
        if coordinate.stateCode:
            searchable_parts.append(coordinate.stateCode)
        searchable_text = " | ".join(searchable_parts).casefold()

        exact_any_groups = [
            filters.sources,
            filters.seasons,
            filters.divisions,
            filters.journeys,
            [_normalize_mode(mode) for mode in filters.modes],
            filters.include_tags_any,
        ]

        for group in exact_any_groups:
            if group and not self._match_any_exact(tags_normalized, group):
                return False

        if filters.include_tags_all and not self._match_all_exact(
            tags_normalized,
            filters.include_tags_all,
        ):
            return False

        if filters.exclude_tags_any and self._match_any_exact(
            tags_normalized,
            filters.exclude_tags_any,
        ):
            return False

        if filters.link_ids:
            normalized_links = {_normalize_token(link_id) for link_id in filters.link_ids}
            if not normalized_links.intersection(link_ids):
                return False

        if filters.country_codes:
            country_code = _normalize_token(coordinate.countryCode or "")
            normalized_country_codes = {
                _normalize_token(code)
                for code in filters.country_codes
            }
            if country_code not in normalized_country_codes:
                return False

        if filters.state_codes:
            state_code = _normalize_token(coordinate.stateCode or "")
            normalized_state_codes = {
                _normalize_token(code)
                for code in filters.state_codes
            }
            if state_code not in normalized_state_codes:
                return False

        if filters.countries:
            countries = [country.casefold() for country in filters.countries]
            if not any(country in searchable_text for country in countries):
                return False

        if filters.text_contains_any:
            queries = [query.casefold() for query in filters.text_contains_any]
            if not any(query in searchable_text for query in queries):
                return False

        return True

    @staticmethod
    def _match_any_exact(tags_normalized: Set[str], values: Sequence[str]) -> bool:
        """Return True if at least one exact token matches."""
        return any(_normalize_token(value) in tags_normalized for value in values)

    @staticmethod
    def _match_all_exact(tags_normalized: Set[str], values: Sequence[str]) -> bool:
        """Return True if all exact tokens match."""
        return all(_normalize_token(value) in tags_normalized for value in values)
