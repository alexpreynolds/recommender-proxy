#!/bin/bash

#https://epilogos.altius.org:9002/?datasetEncoded=GORKIN&datasetAltname=vD&assembly=mm10&stateModel=15&groupEncoded=All_65_epigenomes&groupAltname=all&saliencyLevel=S1&saliencyLevelAltname=KL&chromosome=chr7&start=44609256&end=44626506&tabixSource=remote&tabixUrlEncoded=http%3A%2F%2Fexplore.altius.org%2Ftabix&databaseUrlEncoded=file%3A%2F%2F%2Fhome%2Fubuntu%2Frecommender-proxy%2Fassets%2FMatrixDatabase&outputDestination=stdout&outputFormat=JSON

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
CHROMOSOME=chr7
START=44609256
END=44626506
TABIX_SOURCE=remote
TABIX_URL_ENCODED=http%3A%2F%2Fexplore.altius.org%2Ftabix
TABIX_URL_DECODED=http://explore.altius.org/tabix
DATABASE_URL_ENCODED=file%3A%2F%2F%2Fhome%2Fubuntu%2Frecommender-proxy%2Fassets%2FMatrixDatabase
DATABASE_URL_DECODED=file:///home/ubuntu/recommender-proxy/assets/MatrixDatabase
OUTPUT_DESTINATION=stdout
OUTPUT_FORMAT=JSON

curl -k "https://localhost:9002/?datasetEncoded=${DATASET_ENCODED}&datasetAltname=${DATASET_ALTNAME}&assembly=${ASSEMBLY}&stateModel=${STATE_MODEL}&groupEncoded=${GROUP_ENCODED}&groupAltname=${GROUP_ALTNAME}&saliencyLevel=${SALIENCY_LEVEL}&saliencyLevelAltname=${SALIENCY_LEVEL_ALTNAME}&chromosome=${CHROMOSOME}&start=${START}&end=${END}&tabixSource=${TABIX_SOURCE}&tabixUrlEncoded=${TABIX_URL_ENCODED}&databaseUrlEncoded=${DATABASE_URL_ENCODED}&outputDestination=${OUTPUT_DESTINATION}&outputFormat=${OUTPUT_FORMAT}"
