SHELL:=/bin/bash

all: RecommenderDatabase_assets

RecommenderDatabase_assets:
	rsync -avzh --stats --progress areynolds@tools0.altiusinstitute.org:/home/ntripician/slurm/RecommenderDatabase ${PWD}

StateScores_assets:
	rsync -avzh --stats --progress areynolds@tools0.altiusinstitute.org:/home/ntripician/StateScores ${PWD}
