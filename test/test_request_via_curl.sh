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
CHROMOSOME=chr2
START=43679000
END=43689000
TABIX_SOURCE=remote
TABIX_URL_ENCODED=http%3A%2F%2Fexplore.altius.org%2Ftabix
TABIX_URL_DECODED=http://explore.altius.org/tabix
DATABASE_URL_ENCODED=file%3A%2F%2F%2Fhome%2Fubuntu%2Frecommender-proxy%2Fassets%2FMatrixDatabase
DATABASE_URL_DECODED=file:///home/ubuntu/recommender-proxy/assets/MatrixDatabase
OUTPUT_DESTINATION=stdout

curl -k "https://localhost:9002/?datasetEncoded=${DATASET_ENCODED}&datasetAltname=${DATASET_ALTNAME}&assembly=${ASSEMBLY}&stateModel=${STATE_MODEL}&groupEncoded=${GROUP_ENCODED}&groupAltname=${GROUP_ALTNAME}&saliencyLevel=${SALIENCY_LEVEL}&saliencyLevelAltname=${SALIENCY_LEVEL_ALTNAME}&chromosome=${CHROMOSOME}&start=${START}&end=${END}&tabixSource=${TABIX_SOURCE}&tabixUrlEncoded=${TABIX_URL_ENCODED}&databaseUrlEncoded=${DATABASE_URL_ENCODED}&outputDestination=${OUTPUT_DESTINATION}"
