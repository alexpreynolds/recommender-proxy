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
import ast
import json

BIN_SIZE = 200

def trueSim(forward, reverse):
  return forward if forward < reverse else reverse

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
  sizes = [10000, 25000, 50000]
  size_keys = ["10k", "25k", "50k"] # used for exemplar keying
  window_finder = [(i, abs(sizes[i] - approx_size)) for i in range(len(sizes))]
  window_finder.sort(key = lambda x:x[1])
  window_scale = window_finder[0][0]
  start = midpoint - sizes[window_scale] * 0.6
  end = midpoint + (sizes[window_scale] * 0.6) - BIN_SIZE
  window_size = sizes[window_scale] // BIN_SIZE
  if start < 0:
    start = 0
    end = sizes[window_finder[0][0]] * 1.1
  return (window_size, start, end, midpoint, sizes[window_scale], size_keys[window_scale])

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
@click.option("-t", "--tabix-source",           type=str,      required=False,    help="Tabix data source (file or remote)",                default="file")
@click.option("-u", "--tabix-url",              type=str,      required=False,    help="Tabix data root URL (file or remote)",              default="file:///net/seq/data/projects/Epilogos/epilogos-by-sample-group")
@click.option("-b", "--database-url",           type=str,      required=False,    help="Database root URL (file)",                          default="file:///home/ntripician/slurm/MatrixDatabase")
@click.option("-o", "--output-destination",     type=str,      required=False,    help="Output destination (regular file or stdout)",       default="regular_file")
@click.option("-O", "--output-filename",        type=str,      required=False,    help="Output filename (if destination is regular file)",  default="MATRIX.bed")
@click.option("-f", "--output-format",          type=str,      required=False,    help="Output format (BED or JSON)",                       default="BED")
@click.option("-v", "--verbose",                is_flag=True,  required=False,    help="Log runtimes",                                      default=False)

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
  (kwargs["window_size"], kwargs["start"], kwargs["end"], kwargs["midpoint"], kwargs["window_width"], kwargs["size_key"]) = windowParameters(**kwargs)

  if kwargs["verbose"]:
    sys.stderr.write("\npadding\n")
    sys.stderr.write("--- {} seconds ---\n".format(time.time() - timeStart))
    timeStart = time.time()

  # pytabix library accepts URI with file or http scheme
  tabix_url = tabixUrl(**kwargs)
  tabix_handle = tabix.open(tabix_url)
  try:
    tabix_query = tabix_handle.query(kwargs["chromosome"], int(kwargs["start"]), int(kwargs["end"]))
  except TypeError as err:
    raise SyntaxError("Error: Could not query the specified interval: {}:{}-{}\n".format(kwargs["chromosome"], kwargs["start"], kwargs["end"]))
  
  if kwargs["verbose"]:
    sys.stderr.write("\ntabix\n")
    sys.stderr.write("--- {} seconds ---\n".format(time.time() - timeStart))
    timeStart = time.time()

  qFrame = pd.DataFrame(tabix_query)
  if qFrame.empty and kwargs["tabix_source"] == "remote":
    raise SyntaxError("Error: Could not query the specified interval: {}:{}-{}\n".format(kwargs["chromosome"], kwargs["start"], kwargs["end"]))

  qLocs = qFrame.iloc[:, 0:3]
  qMatrix = qFrame.iloc[:, 3:].astype('float')

  states = qMatrix.idxmax(axis=1) - 3
  scores = qMatrix.sum(axis=1)

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

  qMatrix = qMatrix[localMaxIndex-kwargs["window_size"]+1:localMaxIndex+1]

  idx, count = np.unique(states.to_numpy(), return_counts=True)
  maxS = idx[np.argmax(count)]

  matrixRev = qMatrix.copy().iloc[::-1].values
  matrix = qMatrix.values

  if kwargs["verbose"]:
    sys.stderr.write("\nquery read in + reverse\n")
    sys.stderr.write("--- {} seconds ---\n".format(time.time() - timeStart))
    timeStart = time.time()

  # Python and numpy do not read URI with file scheme
  database_path = databasePath(**kwargs)
  fileName = os.path.join(database_path, "State" + str(maxS + 1))
  fileLocs = pd.DataFrame(data=np.load(fileName + "-Locs.npz", allow_pickle=True)["arr"])
  fileMatrix = np.load(fileName + "-Matrix.npz")["arr"]

  if kwargs["verbose"]:
    sys.stderr.write("\ndatabase read in\n")
    sys.stderr.write("--- {} seconds ---\n".format(time.time() - timeStart))
    timeStart = time.time()

  fileLocs.columns = ["chr", "start", "end"]
  fileLocs['sim_forward'] = np.linalg.norm(fileMatrix - matrix, axis=(1,2))
  fileLocs['sim_rev'] = np.linalg.norm(fileMatrix - matrixRev, axis=(1,2))
  
  fileLocs["sim"] = fileLocs.apply(func=lambda row: trueSim(row["sim_forward"], row["sim_rev"]), axis=1)

  fileLocs = fileLocs.sort_values(["sim"])

  if len(fileLocs) > 100:
    fileLocs = fileLocs[:100]

  if kwargs["verbose"]:
    sys.stderr.write("\nsimilarity + sort\n")
    sys.stderr.write("--- {} seconds ---\n".format(time.time() - timeStart))
    timeStart = time.time()

  # write results to regular file or to standard output
  if kwargs["output_destination"] == "regular_file" and kwargs["output_format"] == "BED":
    with open(kwargs["output_filename"], "w") as f:
      for index, row in fileLocs.iterrows():
        line = "{}\t{}\t{}\n".format(row["chr"], row["start"], row["end"])
        f.write(line)
      if kwargs["verbose"]:
        sys.stderr.write("\nbed file\n")
        sys.stderr.write("--- {} seconds ---\n".format(time.time() - timeStart))
  elif kwargs["output_destination"] == "stdout" and kwargs["output_format"] == "BED":
    for index, row in fileLocs.iterrows():
      line = "{}\t{}\t{}\n".format(row["chr"], row["start"], row["end"])
      sys.stdout.write(line)
  elif kwargs["output_destination"] == "stdout" and kwargs["output_format"] == "JSON":
    # query object setup
    query_chromosome = kwargs["chromosome"]
    padding = int(kwargs["window_width"]) // 2
    query_start = int(kwargs["midpoint"]) - padding
    query_end = int(kwargs["midpoint"]) + padding
    bin_offset = query_start % BIN_SIZE
    query_start -= bin_offset
    query_end -= bin_offset    
    query_midpoint = kwargs["midpoint"] - (bin_offset // 2) 
    query_size_key = kwargs["size_key"]
    results = {
      "query" : {
        "chromosome" : query_chromosome,
        "start" : query_start,
        "end" : query_end,
        "midpoint" : query_midpoint,
        "sizeKey" : query_size_key
      },
      "hits" : ""
    }
    hits_list = []
    for index, (index_label, row) in enumerate(fileLocs.iterrows()):
      line = "{}\t{}\t{}\n".format(row["chr"], row["start"], row["end"])
      if index != 0:
        hits_list.append(line)
      elif row["chr"] != kwargs["chromosome"]: 
        hits_list.append(line)
      elif row["chr"] == kwargs["chromosome"] and (int(row["end"]) < kwargs["start"] or int(row["start"]) > kwargs["end"]):
        hits_list.append(line)
    results["hits"] = ''.join(hits_list)
    sys.stdout.write(json.dumps(results, ensure_ascii=False))
  else:
    raise SystemError("Error: Unknown output destination type and/or format specified\n")

  if kwargs["verbose"]:
    sys.stderr.write("\n___-----___-----___-----___-----___--\n")
    sys.stderr.write("\nTotal Time\n")
    sys.stderr.write("--- {} seconds ---\n".format(time.time() - totalTime))

if __name__ == "__main__":
  main()