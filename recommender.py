#!/usr/bin/env python3

import math
import numpy as np
import pandas as pd
import tabix
import sys
import time
import click
import os
import re
import requests
import urllib.parse

def cosSim(search, query):
  dot = np.dot(search, query)
  norm1 = np.linalg.norm(query)
  norm2 = np.linalg.norm(search)
  return dot / (norm1 * norm2)

def patternSim(search, query):
  return np.divide(np.count_nonzero(np.equal(search, query), axis=0), len(search))

def sim(queryStates, queryScores, searchStates, searchScores, patternWeight, shapeWeight):
  pattern = np.apply_along_axis(patternSim, 1, searchStates, queryStates)
  shape = np.apply_along_axis(cosSim, 1, searchScores, queryScores)
  pattern = pattern * patternWeight
  shape = shape * shapeWeight
  return pattern + shape

def trueSim(forward, reverse):
  return forward if forward > reverse else reverse

def tabixUrl(**kwargs):
  url = None
  source = kwargs["tabix_source"]
  tabix_root_url = kwargs["tabix_url"]
  dataset = kwargs["dataset"]
  dataset_altname = kwargs["dataset_altname"]
  assembly = kwargs["assembly"]
  state_model = kwargs["state_model"]
  if source == "file":
    group = kwargs["group"]
    saliency_level = kwargs["saliency_level"]
    dataset_dirmap = {
      "ROADMAP" : "human/Roadmap_Consortium_127_sample",
      "ADSERA"  : "human/Adsera_et_al_833_sample",
      "GORKIN"  : "mouse/Gorkin_et_al_65_sample"
    }
    try:
      dataset_dir = dataset_dirmap[dataset]
    except KeyError as e:
      raise SystemError("Error: {} dataset not in directory map")
    mode = "single"
    root_fn = "scores.txt.gz"
    # filesystem URL
    url = "{}/{}/{}/{}/{}/{}/{}/{}".format(tabix_root_url, dataset_dir, assembly, mode, state_model, group, saliency_level, root_fn)
    # does the tabix file actually exist? 
    url_parse = urllib.parse.urlparse(url)
    raw_path = os.path.abspath(os.path.join(url_parse.netloc, url_parse.path))
    if not os.path.exists(raw_path):
      raise SystemError("Error: Tabix URL not found on filesystem: {}\n".format(url))
  elif source == "remote":
    # we use alternative name variables to access data via an older name scheme
    group_altname = kwargs["group_altname"]
    saliency_level_altname = kwargs["saliency_level_altname"]
    # remote URL
    url = "{}/{}/{}.{}.{}.{}.gz".format(tabix_root_url, dataset_altname, assembly, state_model, group_altname, saliency_level_altname)
    # validate URL format
    remote_regex = re.compile(
      r"^(?:http|ftp)s?://" # http:// or https://
      r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|" # domain...
      r"localhost|" # localhost...
      r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})" # ...or ip
      r"(?::\d+)?" # optional port
      r"(?:/?|[/?]\S+)$", re.IGNORECASE)
    if re.match(remote_regex, url) is None:
      raise SystemError("Error: Tabix URL is not in valid format: {}\n".format(url))
    # does URL point to somewhere legitimate?
    try:
      with requests.get(url, stream=True) as response:
        try:
          response.raise_for_status()
        except requests.exceptions.HTTPError:
          raise SystemError("Error: Cannot access tabix URL: {}\n".format(url))
    except requests.exceptions.ConnectionError:
      raise SystemError("Error: Cannot access tabix URL: {}\n".format(url))
  return url

def databasePath(**kwargs):
  url = "{}/{}/{}/{}/{}/{}/{}k".format(kwargs["database_url"], kwargs["dataset"], kwargs["assembly"], kwargs["state_model"], kwargs["group"], kwargs["saliency_level"], kwargs["window_size"] // 5)
  # does the database file actually exist?
  url_parse = urllib.parse.urlparse(url)
  raw_path = os.path.abspath(os.path.join(url_parse.netloc, url_parse.path))  
  if not os.path.exists(raw_path):
    raise SystemError("Error: Database URL not found on filesystem: {}\n".format(url))
  return raw_path
  
def windowParameters(**kwargs):
  window_size = None
  start = kwargs["start"]
  end = kwargs["end"]
  approx_size = end - start
  midpoint = start + (approx_size // 2)
  if (approx_size < 30000):
    start = midpoint - 7500
    end = midpoint + 7300
    window_size = 50
    if (start < 0):
      start = 0
      end = 12500
  elif (approx_size < 75000):
    start = midpoint - 37500
    end = midpoint + 37300
    window_size = 250
    if (start < 0):
      start = 0
      end = 62500
  elif (approx_size < 150000):
    start = midpoint - 75000
    end - midpoint + 74800
    window_size = 500
    if (start < 0):
      start = 0
      end = 1250000
  else:
    start = midpoint - 150000
    end = midpoint + 149800
    window_size = 1000
    if (start < 0):
      start = 0
      end = 250000
  return (window_size, start, end)

@click.command()
@click.option("-d", "--dataset",                type=str,      required=True,     help="Source publication or dataset (ROADMAP, ADSERA, or GORKIN)")
@click.option("-D", "--dataset-altname",        type=str,      required=False,    help="Source publication or dataset (using \"old\" naming scheme, e.g., vA, vC, or vD)")
@click.option("-a", "--assembly",               type=str,      required=True,     help="Genomic assembly (hg19, hg38, or mm10)")
@click.option("-m", "--state-model",            type=int,      required=True,     help="State model (15, 18, or 25 for ROADMAP; 15 or 18 for ADSERA; 15 for GORKIN)")
@click.option("-g", "--group",                  type=str,      required=True,     help="Individual dataset group name (using \"new\" naming scheme, ref. /net/seq/data/projects/Epilogos/epilogos-by-sample-group)")
@click.option("-G", "--group-altname",          type=str,      required=False,    help="Individual dataset group name (using \"old\" naming scheme)")
@click.option("-l", "--saliency-level",         type=str,      required=True,     help="Saliency level (S1, S2, or S3)")
@click.option("-L", "--saliency-level-altname", type=str,      required=False,    help="Saliency level, old naming scheme (KL, KLs, or KLss)")
@click.option("-c", "--chromosome",             type=str,      required=True,     help="Query chromosome")
@click.option("-s", "--start",                  type=int,      required=True,     help="Query start position")
@click.option("-e", "--end",                    type=int,      required=True,     help="Query end position")
@click.option("-p", "--pattern",                type=float,    required=False,    help="Weight of Query Pattern, out of 1",                 default=0.35)
@click.option("-h", "--shape",                  type=float,    required=False,    help="Weight of Query Shape, out of 1",                   default=0.65)
@click.option("-t", "--tabix-source",           type=str,      required=False,    help="Tabix data source (file or remote)",                default="file")
@click.option("-u", "--tabix-url",              type=str,      required=False,    help="Tabix data root URL (file or remote)",              default="file:///net/seq/data/projects/Epilogos/epilogos-by-sample-group")
@click.option("-b", "--database-url",           type=str,      required=False,    help="Database root URL (file)",                          default="file:///home/ntripician/slurm/RecommenderDatabase")
@click.option("-o", "--output-destination",     type=str,      required=False,    help="Output destination (regular file or stdout)",       default="regular_file")
@click.option("-O", "--output-filename",        type=str,      required=False,    help="Output filename (if destination is regular file)",  default="FAST.bed")
@click.option("-v", "--verbose",                type=bool,     required=False,    help="Log runtimes",                                      default=False)

def main(**kwargs):
  """
  This program's purpose is to find other regions, given an input region and dataset parameters
  """
  if kwargs["verbose"]:
    totalTime = time.time()
    timeStart = time.time()

    sys.stderr.write("\nread Parameters\n")
    sys.stderr.write("--- {} seconds ---\n".format(time.time() - timeStart))
    timeStart = time.time()

  # window parameters
  (kwargs["window_size"], kwargs["start"], kwargs["end"]) = windowParameters(**kwargs)

  if kwargs["verbose"]:
    sys.stderr.write("\npadding\n")
    sys.stderr.write("--- {} seconds ---\n".format(time.time() - timeStart))
    timeStart = time.time()

  # pytabix library accepts URI with file or http scheme
  tabix_url = tabixUrl(**kwargs)
  tabix_handle = tabix.open(tabix_url)
  tabix_query = tabix_handle.query(kwargs["chromosome"], kwargs["start"], kwargs["end"])
  
  if kwargs["verbose"]:
    sys.stderr.write("\ntabix\n")
    sys.stderr.write("--- {} seconds ---\n".format(time.time() - timeStart))
    timeStart = time.time()

  qFrame = pd.DataFrame(tabix_query)

  qLocs = qFrame.iloc[:, 0:3]
  qScores = qFrame.iloc[:, 3:].astype("float")

  states = qScores.idxmax(axis=1) - 3
  scores = qScores.sum(axis=1)

  avgScore = scores.rolling(kwargs["window_size"]).mean()
  avgScore = avgScore[kwargs["window_size"]-1:]
  avgScore = avgScore.to_frame()
  avgScore.columns = ["score"]

  avgScore["index"] = avgScore.index
  avgScore["max"] = None

  localMaxIndex = avgScore["index"].iloc[0]
  prevIndex = localMaxIndex

  for currentIndex, row in avgScore.iterrows():
    # if the window the loop is looking at is higher scoring than the local Maxium scoring region it is keeping track of
    if row["score"] > avgScore.loc[localMaxIndex, "score"]:
      # keeps track of new local max
      localMaxIndex = currentIndex
    prevIndex = currentIndex

  states = states[localMaxIndex-kwargs["window_size"]+1:localMaxIndex+1]
  scores = scores[localMaxIndex-kwargs["window_size"]+1:localMaxIndex+1]

  idx, count = np.unique(states.to_numpy(), return_counts=True)
  maxS = idx[np.argmax(count)]

  statesRev = states.copy().iloc[::-1]
  statesRev.columns = [i + 3 for i in range(kwargs["window_size"])]

  scoresRev = scores.copy().iloc[::-1]
  scoresRev.columns = [i + 3 for i in range(kwargs["window_size"])]

  if kwargs["verbose"]:
    sys.stderr.write("\nquery read in + reverse\n")
    sys.stderr.write("--- {} seconds ---".format(time.time() - timeStart))
    timeStart = time.time()

  # Python and numpy do not read URI with file scheme
  database_path = databasePath(**kwargs)
  fileName = os.path.join(database_path, "State" + str(maxS + 1))
  fileLocs = pd.DataFrame(data=np.load(fileName + "-Locs.npz", allow_pickle=True)["arr"])
  fileStates = np.load(fileName + "-States.npz")["arr"]
  fileScores = np.load(fileName + "-Scores.npz")["arr"]

  if kwargs["verbose"]:
    sys.stderr.write("\ndatabase read in\n")
    sys.stderr.write("--- {} seconds ---\n".format(time.time() - timeStart))
    timeStart = time.time()

  fileLocs.columns = ["chr", "start", "end"]
  fileLocs["sim_forward"] = sim(states.values, scores.values, fileStates, fileScores, kwargs["pattern"], kwargs["shape"])
  fileLocs["sim_rev"] = sim(statesRev.values, scoresRev.values, fileStates, fileScores, kwargs["pattern"], kwargs["shape"])

  fileLocs["sim"] = fileLocs.apply(func=lambda row: trueSim(row["sim_forward"], row["sim_rev"]), axis=1)

  fileLocs = fileLocs.sort_values(["sim"], ascending=False)

  if len(fileLocs) > 100:
    fileLocs = fileLocs[:100]

  if kwargs["verbose"]:
    sys.stderr.write("\nsimilarity + sort\n")
    sys.stderr.write("--- {} seconds ---\n".format(time.time() - timeStart))
    timeStart = time.time()

  # write results to regular file or to standard output
  if kwargs["output_destination"] == "regular_file":
    with open(kwargs["output_filename"], "w") as f:
      for index, row in fileLocs.iterrows():
        line = "{}\t{}\t{}\n".format(row["chr"], row["start"], row["end"])
        f.write(line)
      if kwargs["verbose"]:
        sys.stderr.write("\nbed file\n")
        sys.stderr.write("--- {} seconds ---\n".format(time.time() - timeStart))
  elif kwargs["output_destination"] == "stdout":
    for index, row in fileLocs.iterrows():
      line = "{}\t{}\t{}\n".format(row["chr"], row["start"], row["end"])
      sys.stdout.write(line)
  else:
    raise SystemError("Error: Unknown output destination type specified\n")

  if kwargs["verbose"]:
    sys.stderr.write("\n___-----___-----___-----___-----___--\n")
    sys.stderr.write("\nTotal Time\n")
    sys.stderr.write("--- {} seconds ---\n".format(time.time() - totalTime))

if __name__ == "__main__":
  main()