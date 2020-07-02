#!/usr/bin/env python3

import sys
import tabix
import numpy as np

try:
  chromosome = sys.argv[1]
  start = int(sys.argv[2])
  bins = int(sys.argv[3])
  binSize = int(sys.argv[4])
  tabixScheme = sys.argv[5]
  tabixHost = sys.argv[6]
  tabixPath = sys.argv[7]
  dataSet = sys.argv[8]
  assembly = sys.argv[9]
  stateModel = sys.argv[10]
  groupShortname = sys.argv[11]
  saliency = sys.argv[12]
  if start <= 0 or bins <= 0 or binSize <= 0:
    raise ValueError
except (IndexError, ValueError):
  sys.stderr.write('Error: Possible format error or input problem\n')
  sys.exit(-1)

def main():
  end = start + (bins * binSize)
  
  url = '{}://{}/{}/{}/{}.{}.{}.{}.gz'.format(tabixScheme, tabixHost, tabixPath, dataSet, assembly, stateModel, groupShortname, saliency)
  
  tb = tabix.open(url)
  
  query = tb.query(chromosome, start, end)
  
  chr = []
  
  for res in query:
    chr.append(res)
    
  lastColumn = 3 + int(stateModel)
  for bin in range(len(chr)):
    for i in range(1, lastColumn):
      if (i < 3):
        chr[bin][i] = int(chr[bin][i])
      else:
        chr[bin][i] = float(chr[bin][i])
  
  states = []
  scores = []
  stateTotals = [0 for i in range(int(stateModel))]
  
  for i in range(50):
    max = 3
    score = 0
    for state in range(3, lastColumn):
      score += chr[i][state]
      if (chr[i][state] > chr[i][max]):
        max = state
    scores.append(score)
    states.append(max - 2)
    stateTotals[max - 3] += 1
    
  maxS = 0
  for i in range(int(stateModel)):
    if (stateTotals[maxS] < stateTotals[i]):
      maxS = i
      
  statesRev = states.copy()
  scoresRev = scores.copy()
  statesRev.reverse()
  scoresRev.reverse()
  
  sComp = []
  fileName = "/home/ubuntu/recommender-proxy/assets/StateScores/State" + str(maxS + 1) + ".bed"
  
  #
  # where does the 52 value come from? (will this work for 18- and 25-state model tests?)
  #
  with open(fileName,'r') as stateFile:
    for line in stateFile:
      l = line.split("\t")
      for i in range(3, 52):
        temp = l[i].split(",")
        l[i] = (int(temp[0][1:]),float(temp[1][1:-1]))  
      temp = l[52].split(",")
      l[52] = (int(temp[0][1:]),float(temp[1][:-2]))
      sComp.append(l)
      
  top = findTop(states, scores, sComp, statesRev, scoresRev)
  top.sort(reverse=True, key=lambda x: x[1])
  if (len(top) > 100):
    top = top[:100]
        
  #print('{}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}'.format(chromosome, start, bins, binSize, tabixScheme, tabixHost, tabixPath, dataSet, assembly, stateModel, groupShortname, saliency))
  
  for line in top:
    sys.stdout.write('{}\t{}\t{}\n'.format(line[0][0], line[0][1], line[0][2]))
  
  sys.exit(0)

def cosSim(vec1, vec2):
  dot = np.dot(vec1, vec2)
  norm1 = np.linalg.norm(vec1)
  norm2 = np.linalg.norm(vec2)
  return dot / (norm1 * norm2)
  
def findTop(state, score, possibilities, statesRev, scoresRev):
  output = []
  for r in possibilities:
    stateCheck = []
    scoreCheck = []
    sim = 0
    simRev = 0
    for i in range(3, 53):
      stateCheck.append(r[i][0])
      scoreCheck.append(r[i][1])

    sim += .35 * cosSim(state, stateCheck)
    sim += .65 * cosSim(score, scoreCheck)

    simRev += .35 * cosSim(statesRev, stateCheck)
    simRev += .65 * cosSim(scoresRev, scoreCheck)

    if (sim > simRev):
      output.append((r, sim))
    else:
      output.append((r, simRev))
  return output

if __name__ == '__main__':
  main()