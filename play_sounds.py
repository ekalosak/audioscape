#!/usr/local/bin/python3
import os
import time
import pathlib as pl
from pathlib import Path
from typing import List
# import logging
# from logging import handlers

import requests
import pandas as pd
import zipfile
import vlc

DEV_MODE=True
RAINY_DAYS=[2, 6]  # wed, sun
OCEAN_DAYS=[0, 1, 4]  # mon, tues, fri
SUNNY_DAYS=[3, 5]  # thurs, sat
DOWNLOAD_DIR="downloads"
SOUNDS_CSV="sound_links.csv"
SOUND_DIR="sounds"
# LOG_DIR="logs"
# LOG_FN=LOG_DIR+"/play_sounds.log"
LOG_MAXBYTES=262144  # 64**3
# DIRS=[DATA_DIR, LOG_DIR]
DIRS=[DOWNLOAD_DIR, SOUND_DIR]
SHORTEST_PLAY=5  # sec; sleep the remainder of this period if played sound is shorter
ALLOWED_SOUNDFILES=['.mp3', '.wav', '.aiff', '.oog', '.flac']

""" TODO
1. Logging to file (how to make logger global?)
"""

def _log(msg: str, head: str="DEBUG", show: bool=True):
    tm = time.asctime()
    s = f"{head} - {tm}: {msg}"
    if show:
        print(s)
def error(msg: str):
    _log(msg, "ERROR")
def info(msg: str):
    _log(msg, "INFO")
def debug(msg: str):
    _log(msg, "DEBUG", show=DEV_MODE)


# def make_logger():
#     logging.basicConfig(format='%(levelname)s:%(asctime): %(message)s', level=logging.DEBUG)
#     logger = logging.getLogger(__name__)
#     return logger
#
# def add_handlers(logger):
#     fhandler = handlers.RotatingFileHandler(
#             filename = LOG_FN,
#             maxBytes = LOG_MAXBYTES,
#             )
#     shandler = handlers.StreamHandler()
#     handlers = [fhandler, shandler]
#     for h in handlers:
#         logger.addHandler(h)
#     return logger


def setup():
    """ create project structure
    """
    dirs = [pl.Path(s) for s in DIRS]
    for d in dirs:
        if not d.exists():
            info(f"Creating directory: {d}")
            d.mkdir()
        else:
            debug(f"{d} already exists")


def load_data(soundscsv: str) -> pd.DataFrame:
    debug(f"reading data from {soundscsv}")
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
        save_path = Path(DOWNLOAD_DIR) / filename
        save_paths.append(save_path)
        if not save_path.exists():
            info(f"downloading {title} from {url} to {save_path}")
            download_url(url, save_path)
        else:
            debug(f"{save_path} already exists")
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

def tod() -> (str, str):
    """ Return whether it is currently Morning, Afternoon, or Night
    """
    # Morning, Afternoon, Night
    hr = time.localtime().tm_hour
    wd = time.localtime().tm_wday
    if hr > 16 and hr <= 21:  # between 4p and 9p
        td = "Afternoon"
    elif hr > 4 and hr <= 11:  # between 4a and 11a
        td = "Morning"
    elif hr > 21 or hr <= 4:  # between 9p and 4a
        td = "Night"
    else:  # between 11a and 4p
        td = "Day"
    if wd in RAINY_DAYS:
        w = "Raining"
    elif wd in OCEAN_DAYS:
        w = "Ocean"
    else:
        w = "Sunny"
    return td, w

def play_from_path(soundpath: Path) -> float:
    """ Play file from <soundpath>, return time played if success or 0 if error
    """
    t0 = time.time()
    try:
        p = vlc.MediaPlayer(soundpath)
        p.play()
        time.sleep(0.1)
        while p.is_playing():
            timeleft = p.get_length() / 1000
            debug(f"sleeping {round(timeleft)} sec until {soundpath} is over")
            time.sleep(timeleft + 0.1)
    except Exception as e:
        error(f"Encountered error playing {soundpath}: {str(e)}")
        return 0.
    t1 = time.time()
    time_played = t1-t0
    debug(f"{soundpath} played for {round(time_played, 2)} seconds")
    return time_played


def play_one(df: pd.DataFrame):
    """ Plays a sound from the <df> matching current local conditions
    """
    t_str, d_str = tod()
    timemask = df['Time'] == t_str
    weathermask = df['Day'] == d_str
    mp3mask = df['mp3path'].notna()
    mask = mp3mask & timemask & weathermask
    if not mask.any():
        raise Exception(f"{SOUNDS_CSV} has no links for <{t_str}, {d_str}>")
    tdf = df[mask]
    row = tdf.sample(1)
    _soundpath = row["mp3path"].values[0]
    title = row["title"].values[0]
    td = row["Time"].values[0]
    weather = row["Day"].values[0]
    info(f"Playing {title} from {_soundpath}, a {td}-time sound for a {weather} day.")
    soundpath = Path(_soundpath)
    time_played = play_from_path(soundpath)
    if time_played < SHORTEST_PLAY and time_played > 0:
        sleeptime = SHORTEST_PLAY - time_played
        debug(f"{soundpath} played for a short time ({round(time_played,4)} sec), sleeping for {round(sleeptime,4)} seconds")
        time.sleep(sleeptime)

def is_sound_file(sound: Path) -> bool:
    return sound.suffix.lower() in ALLOWED_SOUNDFILES

def unzip(zippaths: pd.Series) -> pd.Series:
    """ Unzip and move mp3s
    """
    extracted_paths = []
    for path in zippaths:
        if not path.suffix == ".zip":
            if is_sound_file(path):
                debug(f"{path} is a sound file, skipping extraction")
                extracted_path = path
            else:
                debug(f"{path} is an unrecognized filetype, skipping")
                extracted_path = None
        else:
            try:
                with zipfile.ZipFile(path, 'r') as zip_ref:
                    mp3filenames = [
                            fr.filename for fr in zip_ref.filelist
                            if is_sound_file(Path(fr.filename))
                            ]
                    if len(mp3filenames) == 0:
                        extracted_path = None
                        debug(f"{path} contains no mp3 files")
                    elif len(mp3filenames) >= 1:
                        mp3filename = mp3filenames[0]
                        if len(mp3filenames) > 1:
                            debug(f"{zip_ref.filename} contains more than one mp3 file, selecting first one")
                        debug(f"extracting {mp3filename}")
                        extracted_path = zip_ref.extract(
                                mp3filename,
                                path=SOUND_DIR
                                )
            except Exception as e:
                error(f"Encountered error unzipping {path}: {str(e)}")
                extracted_path = None
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
