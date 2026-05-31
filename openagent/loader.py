from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openagent.game_assets.bundle import GameBundle


@dataclass(frozen=True)
class EpisodeAssets:
    episode: int
    exe: Path | None
    cfg: Path | None
    screens: dict[str, list[Path]]
    gfx16: Path | None
    gfx8: Path | None
    levels: Path | None
    sounds: list[Path]


@dataclass
class Campaign:
    source: Path
    bundle: "GameBundle"
    assets: dict[int, EpisodeAssets]

    @property
    def episode_numbers(self) -> list[int]:
        return sorted(self.bundle.episodes)

    def cleanup(self) -> None:
        self.bundle.cleanup()



def load_campaign(source: Path) -> Campaign:
    from openagent.game_assets.bundle import load_game

    bundle = load_game(source)
    assets = {ep: scan_episode_assets(bundle.source, ep) for ep in sorted(bundle.episodes)}
    return Campaign(source=source, bundle=bundle, assets=assets)


def find_case_insensitive(root: Path, name: str) -> Path | None:
    wanted = name.lower()
    direct = root / wanted
    if direct.exists():
        return direct
    for path in root.rglob("*"):
        if path.is_file() and path.name.lower() == wanted:
            return path
    return None


def find_many(root: Path, names: list[str]) -> list[Path]:
    found: list[Path] = []
    for name in names:
        path = find_case_insensitive(root, name)
        if path is not None:
            found.append(path)
    return found


def scan_episode_assets(root: Path, episode: int) -> EpisodeAssets:
    prefix = f"SAM{episode}"
    screens = {
        "apogee": find_many(root, [f"{prefix}.APO"]),
        "title": find_many(root, [f"{prefix}.TTL"]),
        "credits": find_many(root, [f"{prefix}.CRD"]),
        "ending": find_many(root, [f"{prefix}.END", f"{prefix}A.END", f"{prefix}B.END"]),
    }
    return EpisodeAssets(
        episode=episode,
        exe=find_case_insensitive(root, f"{prefix}.EXE"),
        cfg=find_case_insensitive(root, f"{prefix}.CFG"),
        screens=screens,
        gfx16=find_case_insensitive(root, f"{prefix}01.GFX"),
        gfx8=find_case_insensitive(root, f"{prefix}02.GFX"),
        levels=find_case_insensitive(root, f"{prefix}03.GFX"),
        sounds=find_many(root, [f"{prefix}01E.SND", f"{prefix}02E.SND", f"{prefix}03E.SND"]),
    )
