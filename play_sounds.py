#!/usr/local/bin/python3
import os
import time
import pathlib as pl
from pathlib import Path

import requests
import pandas as pd
import zipfile

SOUNDS_CSV="sound_links.csv"
LINK="http://www.orangefreesounds.com/wp-content/uploads/2020/03/Sounds-of-spring.zip"
DATA_DIR="sounds"

def _log(msg: str, head: str="DEBUG"):
    tm = time.asctime()
    print(f"{head} - {tm}: {msg}")
def info(msg: str):
    _log(msg, "INFO")
def debug(msg: str):
    _log(msg, "DEBUG")


def setup():
    """ create project structure
    """
    dl_dir = pl.Path(DATA_DIR)
    if not dl_dir.exists():
        debug(f"Creating download directory: {dl_dir}")
        dl_dir.mkdir()


def load_data(soundscsv: str) -> pd.DataFrame:
    sdf=pd.read_csv(soundscsv)
    return sdf


def download(links_and_titles: pd.DataFrame) -> pd.Series:
    """ Download the links in the URL column if they don't exist already
    """
    save_paths = []
    for i, row in links_and_titles.iterrows():
        url = row["URL"]
        title = row["title"]
        filename = url.split("/")[-1]
        save_path = Path(DATA_DIR) / filename
        if not save_path.exists():
            debug(f"downloading {title} from {url} to {save_path}")
            download_url(url, save_path)
        else:
            debug(f"{save_path} already exists")
        save_paths.append(save_path)
    return pd.Series(save_paths)


def download_url(url, save_path, chunk_size=128):
    """
    :param url: from where to download
    :param save_path: to where to download
    """
    try:
        r = requests.get(url, stream=True)
        with open(save_path, 'wb') as fd:
            for chunk in r.iter_content(chunk_size=chunk_size):
                fd.write(chunk)
        return 0
    except Exception as e:
        debug("Encountered error downloading from {url}:\nstr(e)")

def tod() -> str:
    """ Return whether it is currently Morning, Afternoon, or Night
    """
    # Morning, Afternoon, Night
    hr = time.localtime().tm_hour
    if hr > 12 and hr < 18:  # between noon and 6p
        return "Afternoon"
    elif hr > 6:  # between 6a and noon
        return "Morning"
    else:
        return "Night"

def play_from_path(soundpath: Path):
    breakpoint()


def play_one(df: pd.DataFrame):
    t_str = tod()
    timemask = df['Time'] == t_str
    mp3mask = df['mp3path'].notna()
    mask = mp3mask & timemask
    if not mask.any():
        raise Exception(f"{SOUNDS_CSV} has no links for time <{t_str}>")
    tdf = df[mask]
    row = tdf.sample(1)
    _soundpath, title = row[["mp3path", "title"]]
    debug(f"playing {title} from {_soundpath}")
    soundpath = Path(_soundpath)
    play_from_path(soundpath)


def unzip(zippaths: pd.Series) -> pd.Series:
    """ Unzip and move mp3s
    """
    extracted_paths = []
    for path in zippaths:
        if not path.suffix == ".zip":
            debug(f"{path} is not a zip file, skipping")
            mp3path = None
            continue
        with zipfile.ZipFile(path, 'r') as zip_ref:
            mp3filenames = [fr.filename for fr in zip_ref.filelist if fr.filename.endswith('.mp3')]
            if len(mp3filenames) == 0:
                extracted_path = None
                debug(f"{path} contains no mp3 files")
            elif len(mp3filenames) >= 1:
                mp3filename = mp3filenames[0]
                if len(mp3filenames) > 1:
                    debug(f"{zip_ref.filename} contains more than one mp3 file, selecting first one")
                debug(f"extracting {mp3filename}")
                extracted_path = zip_ref.extract(mp3filename, path=DATA_DIR)
        extracted_paths.append(extracted_path)
    return pd.Series(extracted_paths)


def main():
    setup()
    df = load_data(SOUNDS_CSV)
    df["title"] = df["Sound theme"].apply(
                lambda s: s.replace(",", "").replace(" ", "_"),
                1
                )
    df["zippath"] = download(df[["URL", "title"]])
    df["mp3path"] = unzip(df["zippath"])
    while 1:
        play_one(df)


if __name__ == '__main__':
    info("START")
    main()
    info("END")
