"""
Pydantic models pour la validation des structures de données.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime


class Extra(BaseModel):
    """Données supplémentaires d'une coordonnée."""
    tags: List[str] = Field(default_factory=list)

    @validator('tags', pre=True)
    def normalize_tags(cls, value):
        """Accepter une liste simple ou un mapping `{tag: {order: n}}`.

        Les exports map-making.app peuvent reassigner les valeurs numeriques
        `order`. On ne conserve donc que leur ordre relatif pour reconstruire
        une liste ordonnee localement.
        """
        if isinstance(value, dict):
            def sort_key(item):
                tag, metadata = item
                if isinstance(metadata, dict):
                    raw_order = metadata.get('order', 10**9)
                    try:
                        normalized_order = int(raw_order)
                    except (TypeError, ValueError):
                        normalized_order = 10**9
                    return (normalized_order, tag.casefold())
                return (10**9, tag.casefold())

            return [tag for tag, _metadata in sorted(value.items(), key=sort_key)]

        return value

    def to_storage_format(self) -> Dict[str, Any]:
        """Exporter un ordre local compact pour les tags.

        Les valeurs 0..N servent au JSON local et comme hint d'ordre relatif
        a l'import. Elles ne sont pas stables apres un round-trip via
        map-making.app.
        """
        return {
            "tags": {
                tag: {"order": index}
                for index, tag in enumerate(self.tags)
            }
        }


class Coordinate(BaseModel):
    """Structure d'une coordonnée compatible map-making.app."""
    lat: float = Field(..., ge=-90, le=90, description="Latitude (-90 à 90)")
    lng: float = Field(..., ge=-180, le=180, description="Longitude (-180 à 180)")
    heading: float = Field(default=0, ge=0, le=360, description="Direction de la caméra (0-360°)")
    pitch: float = Field(default=0, description="Angle vertical de la caméra")
    zoom: float = Field(default=0)
    panoId: Optional[str] = None
    countryCode: Optional[str] = None
    stateCode: Optional[str] = None
    extra: Extra = Field(default_factory=Extra)
    id: int = Field(default=-1, description="ID interne map-making.app")
    flags: int = Field(default=0, description="Flags internals")
    createdAt: Optional[str] = None

    @validator('createdAt', pre=True, always=True)
    def set_created_at(cls, v):
        """Défaut à l'heure actuelle si non fourni."""
        if v is None:
            return datetime.utcnow().isoformat() + 'Z'
        return v

    def to_mma_format(self) -> Dict[str, Any]:
        """Convertir au format map-making.app pour l'API."""
        return {
            "id": self.id,
            "flags": self.flags,
            "location": {
                "lat": self.lat,
                "lng": self.lng
            },
            "panoId": self.panoId,
            "heading": self.heading,
            "pitch": self.pitch,
            "zoom": self.zoom,
            "tags": self.extra.tags,
            "createdAt": self.createdAt or datetime.utcnow().isoformat() + 'Z'
        }

    def to_storage_format(self) -> Dict[str, Any]:
        """Convertir au format JSON local en conservant les tags par location."""
        return self.model_dump() if hasattr(self, "model_dump") else self.dict()


class MapData(BaseModel):
    """Structure complète d'une map compatible map-making.app."""
    name: str = Field(..., description="Nom de la map")
    customCoordinates: List[Coordinate] = Field(
        default_factory=list,
        description="Liste des coordonnées"
    )

    extra: Optional[Extra] = None

    class Config:
        json_encoders = {
            Coordinate: lambda v: v.dict()
        }

    def get_stats(self) -> Dict[str, int]:
        """Retourner les statisques de la map."""
        return {
            "total_coordinates": len(self.customCoordinates),
            "coordinates_with_pano": sum(1 for c in self.customCoordinates if c.panoId),
            "coordinates_with_country": sum(1 for c in self.customCoordinates if c.countryCode),
        }

    def to_storage_format(self) -> Dict[str, Any]:
        """Convertir la map au format JSON local."""
        data = {
            "name": self.name,
            "customCoordinates": [
                coordinate.to_storage_format()
                for coordinate in self.customCoordinates
            ],
        }
        if self.extra:
            data["extra"] = self.extra.to_storage_format()
        return data


class SourceMapItem(BaseModel):
    """Structure d'un item du fichier source coordinatesAllTags.json."""
    link: str
    name: str
    tags: List[str]
    coordinates: List[Dict[str, Any]]


class DiffStats(BaseModel):
    """Statistiques de diff entre deux versions."""
    added: int = 0
    removed: int = 0
    modified: int = 0
    timestamp_before: datetime
    timestamp_after: datetime
    checksum_before: str
    checksum_after: str
