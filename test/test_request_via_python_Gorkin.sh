#!/bin/bash

DATASET_ENCODED=GORKIN
DATASET_DECODED=GORKIN
DATASET_ALTNAME=vD
ASSEMBLY=mm10
STATE_MODEL=15
GROUP_ENCODED=All_65_epigenomes
GROUP_DECODED=All_65_epigenomes
GROUP_ALTNAME=all
SALIENCY_LEVEL=S1
SALIENCY_LEVEL_ALTNAME=KL
CHROMOSOME=chr9
START=3025200
END=3035400
TABIX_SOURCE=remote
TABIX_URL_ENCODED=http%3A%2F%2Fexplore.altius.org%2Ftabix
TABIX_URL_DECODED=http://explore.altius.org/tabix
DATABASE_URL_ENCODED=file%3A%2F%2F%2Fhome%2Fubuntu%2Frecommender-proxy%2Fassets%2FMatrixDatabase
DATABASE_URL_DECODED=file:///home/ubuntu/recommender-proxy/assets/MatrixDatabase
OUTPUT_DESTINATION=stdout
OUTPUT_FORMAT=JSON

echo "../recommender.py --dataset ${DATASET_DECODED} --dataset-altname ${DATASET_ALTNAME} --assembly ${ASSEMBLY} --state-model ${STATE_MODEL} --group ${GROUP_ENCODED} --group-altname ${GROUP_ALTNAME} --saliency-level ${SALIENCY_LEVEL} --saliency-level-altname ${SALIENCY_LEVEL_ALTNAME} --chromosome ${CHROMOSOME} --start ${START} --end ${END} --tabix-source ${TABIX_SOURCE} --tabix-url ${TABIX_URL_DECODED} --database-url ${DATABASE_URL_DECODED} --output-destination ${OUTPUT_DESTINATION} --output-format ${OUTPUT_FORMAT}"

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
		  --output-destination ${OUTPUT_DESTINATION} \
		  --output-format ${OUTPUT_FORMAT}
