# simsearch-proxy

A web backend for the SimSearch results generated via the [epilogos](https://github.com/meuleman/epilogos) pipeline.

## Setup

Run `npm install` to install dependencies. Use the `recommender-proxy.development.json` file with PM2 to set up a web application. 

Tabix index files will be stored locally in a subdirectory of the system temporary directory (`/tmp/dhsIndex` or `/tmp/recommender`). If tabix files are updated, it is recommended to clear the contents of these folders, so that fresh index files are requested.

Note: Valid SSL certificates are required. Root access to PM2 may be required if file permissions on SSL certs require it.
