"""
CLI for generating filtered GeoGuessr maps from pipeline output.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Optional

from logger import setup_logger
from map_builder import MapBuildSpec, MapBuilder, MapFilterSpec

logger = setup_logger(__name__)


def _appendable_argument(parser: argparse.ArgumentParser, *names: str, help_text: str) -> None:
    """Register an argument that can be repeated."""
    parser.add_argument(*names, action="append", default=[], help=help_text)


def _build_single_spec(args: argparse.Namespace) -> MapBuildSpec:
    """Build one map specification from CLI arguments."""
    if not args.name:
        raise ValueError("--name est requis hors mode --spec-file")

    filters = MapFilterSpec(
        sources=args.source_tag,
        seasons=args.season,
        divisions=args.division,
        journeys=args.journey,
        modes=args.mode,
        countries=args.country,
        country_codes=args.country_code,
        state_codes=args.state_code,
        include_tags_all=args.include_tag_all,
        include_tags_any=args.include_tag_any,
        exclude_tags_any=args.exclude_tag,
        text_contains_any=args.text,
        link_ids=args.link_id,
        sample_size=args.sample_size,
        sample_seed=args.sample_seed,
        limit=args.limit,
    )

    return MapBuildSpec(
        name=args.name,
        source_file=Path(args.source_file) if args.source_file else None,
        output_file=Path(args.output_file) if args.output_file else None,
        upload=args.upload,
        map_id=args.map_id,
        public_url=args.public_url,
        chunk_size=args.chunk_size,
        filters=filters,
    )


def _print_summary(results: List) -> None:
    """Log a short summary for generated maps."""
    logger.info("=" * 60)
    logger.info("GENERATION TERMINEE")
    for result in results:
        upload_info = result.uploaded_map_id or "-"
        logger.info(
            "%s | %s/%s coordonnees | output=%s | map_id=%s",
            result.map_data.name,
            result.selected_count,
            result.source_count,
            result.output_file,
            upload_info,
        )
    logger.info("=" * 60)


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Generer des maps GeoGuessr filtrees depuis le JSON de la pipeline",
    )

    parser.add_argument(
        "--spec-file",
        type=str,
        help="Fichier JSON contenant plusieurs maps a generer",
    )
    parser.add_argument(
        "--name",
        type=str,
        help="Nom de la map a generer",
    )
    parser.add_argument(
        "--source-file",
        type=str,
        help="Fichier source (defaut: data/La ligue.json)",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        help="Fichier JSON de sortie",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Uploader la map vers map-making.app",
    )
    parser.add_argument(
        "--map-id",
        type=str,
        help="Mettre a jour une map existante au lieu d'en creer une",
    )
    parser.add_argument(
        "--public-url",
        type=str,
        help="Slug public map-making.app a appliquer",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=500,
        help="Nombre de coordonnees par lot a l'upload (defaut: 500)",
    )

    _appendable_argument(parser, "--source-tag", help_text="Source exacte: La Ligue, Cactus...")
    _appendable_argument(parser, "--season", help_text="Tag exact de saison: S5")
    _appendable_argument(parser, "--division", help_text="Tag exact de division: L1, L2...")
    _appendable_argument(parser, "--journey", help_text="Tag exact de journee: J0, J1...")
    _appendable_argument(parser, "--mode", help_text="Mode GeoGuessr: Solo, NM, Move, NMPZ...")
    _appendable_argument(parser, "--country", help_text="Recherche texte dans les tags: France, Mexique...")
    _appendable_argument(parser, "--country-code", help_text="Code pays exact: FR, MX...")
    _appendable_argument(parser, "--state-code", help_text="Code region exact")
    _appendable_argument(parser, "--include-tag-all", help_text="Tag exact obligatoire, repetable")
    _appendable_argument(parser, "--include-tag-any", help_text="Au moins un de ces tags exacts")
    _appendable_argument(parser, "--exclude-tag", help_text="Tag exact a exclure")
    _appendable_argument(parser, "--text", help_text="Texte a chercher dans les tags")
    _appendable_argument(parser, "--link-id", help_text="Valeur du tag link=... a inclure")

    parser.add_argument(
        "--sample-size",
        type=int,
        help="Tirer un sous-ensemble aleatoire de cette taille",
    )
    parser.add_argument(
        "--sample-seed",
        type=int,
        default=42,
        help="Seed deterministe pour l'echantillonnage (defaut: 42)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limiter au nombre final de coordonnees",
    )

    args = parser.parse_args()
    builder = MapBuilder()

    try:
        if args.spec_file:
            results = builder.build_from_batch_file(Path(args.spec_file))
        else:
            spec = _build_single_spec(args)
            result = builder.build_map(spec)
            builder.save_result(result)
            if spec.upload:
                builder.upload_result(result)
            results = [result]

        _print_summary(results)
        raise SystemExit(0)

    except Exception as exc:
        logger.error("Generation echouee: %s", exc, exc_info=True)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
