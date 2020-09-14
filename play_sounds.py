#!/usr/local/bin/python3
import os
import time
import pathlib as pl
from pathlib import Path

import requests
import pandas as pd

SOUNDS_CSV="sound_links.csv"
LINK="http://www.orangefreesounds.com/wp-content/uploads/2020/03/Sounds-of-spring.zip"
DL_DIR="sounds"

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
    dl_dir = pl.Path(DL_DIR)
    if not dl_dir.exists():
        debug(f"Creating download directory: {dl_dir}")
        dl_dir.mkdir()


def load_data(soundscsv: str) -> pd.DataFrame:
    sdf=pd.read_csv(soundscsv)
    return sdf


def download(links_and_titles: pd.DataFrame) -> pd.Series:
    """
    """
    for i, row in links_and_titles.iterrows():
        url = row["URL"]
        title = row["title"]
        filename = url.split("/")[-1]
        save_path = Path(DL_DIR) / filename
        if not save_path.exists():
            debug(f"downloading {title} from {url} to {save_path}")
            download_url(url, save_path)
        else:
            debug(f"{save_path} already exists")


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


def main():
    setup()
    df = load_data(SOUNDS_CSV)
    df["title"] = df["Sound theme"].apply(
                lambda s: s.replace(",", "").replace(" ", "_"),
                1
                )
    df["path"] = download(df[["URL", "title"]])
    # TODO time relevant play
    play(df[["path", "title"]])


if __name__ == '__main__':
    info("START")
    main()
    info("END")
