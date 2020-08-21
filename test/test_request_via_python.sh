#!/bin/bash

DATASET_ENCODED=ROADMAP
DATASET_DECODED=ROADMAP
DATASET_ALTNAME=vA
ASSEMBLY=hg19
STATE_MODEL=15
GROUP_ENCODED=All_127_Roadmap_epigenomes
GROUP_DECODED=All_127_Roadmap_epigenomes
GROUP_ALTNAME=all
SALIENCY_LEVEL=S1
SALIENCY_LEVEL_ALTNAME=KL
CHROMOSOME=chr7
START=5562760
END=5573040
TABIX_SOURCE=remote
TABIX_URL_ENCODED=http%3A%2F%2Fexplore.altius.org%2Ftabix
TABIX_URL_DECODED=http://explore.altius.org/tabix
DATABASE_URL_ENCODED=file%3A%2F%2F%2Fhome%2Fubuntu%2Frecommender-proxy%2Fassets%2FMatrixDatabase
DATABASE_URL_DECODED=file:///home/ubuntu/recommender-proxy/assets/MatrixDatabase
OUTPUT_DESTINATION=stdout

echo "../recommender.py --dataset ${DATASET_DECODED} --dataset-altname ${DATASET_ALTNAME} --assembly ${ASSEMBLY} --state-model ${STATE_MODEL} --group ${GROUP_ENCODED} --group-altname ${GROUP_ALTNAME} --saliency-level ${SALIENCY_LEVEL} --saliency-level-altname ${SALIENCY_LEVEL_ALTNAME} --chromosome ${CHROMOSOME} --start ${START} --end ${END} --tabix-source ${TABIX_SOURCE} --tabix-url ${TABIX_URL_DECODED} --database-url ${DATABASE_URL_DECODED} --output-destination ${OUTPUT_DESTINATION}"

../recommender.py --dataset ${DATASET_DECODED} \
		  --dataset-altname ${DATASET_ALTNAME} \
		  --assembly ${ASSEMBLY} \
		  --state-model ${STATE_MODEL} \
		  --group ${GROUP_ENCODED} \
		  --group-altname ${GROUP_ALTNAME} \
		  --saliency-level ${SALIENCY_LEVEL} \
		  --saliency-level-altname ${SALIENCY_LEVEL_ALTNAME} \
		  --chromosome ${CHROMOSOME} \
		  --start ${START} \
		  --end ${END} \
		  --tabix-source ${TABIX_SOURCE} \
		  --tabix-url ${TABIX_URL_DECODED} \
		  --database-url ${DATABASE_URL_DECODED} \
		  --output-destination ${OUTPUT_DESTINATION}
